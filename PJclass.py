import socket
import time

"""
class Projector.
    класс для управления проектором по протоколу PJlink.
    Для инициализации необоходимо указать ip, порт выставлен по умолчанию 4352.
    
    Пример инициализации для сетапа из 4 проекторов
        pr[0] = Projector('192.168.0.8')
        pr[1] = Projector('192.168.0.9')
        pr[2] = Projector('192.168.0.10')
        pr[3] = Projector('192.168.0.11')
                
        
    Методы и атрибуты с префиксом '__', например self.__socket или __cmd_send() внутренние и подразумевается,
    что пользователь ими не пользуется и не пытается поменять.
    
    Пример сеанса связи: 
        if pr.open_connection():                                        # открыли соединение
            if not pr.set_shutter(1):                                   # Включили заслонку
                print("result of connect: 0x%x" % pr.getlasterror())
            res, lmp_inf = pr.get_lamp_info()                           # Запросили инфу о лампах
            if res:
                print('Lamp info: ', lmp_inf)
            else:
                print("Unable to get lamp info. Error code: 0x%x" % pr.getlasterror())
                    
        else:
            print("result of connect: 0x%x" % pr.getlasterror())
        pr.close_connection()                                           # обязательно закрыли за собой дверь
   
    
    Команды делятся на 2 типа: set и get.
    Все команды возвращают True при получении от проектора подтверждения выполнения
    команды(см. спецификацию PJlink) и False в противном случае. 
    
    При получении False можно узнать причину и запросить код ошибки
    c помощью метода getlasterror() (см. class ErrCode)
    
    Команда set устанавливает какой либо параметр. Возвращает True/False
    Пример управления shutter
        if not pr[2].set_shutter(0):
            print('Что-то пошло не так. Код ошибки: 0x%x' % pr[2].getlasterror())
    
    Команда get запрашивает установленные параметры. Возвращает True и param или False и пустой объект param
    Формат param зависит от конкретной команды, в основном это набор числовых параметров
        res, lmp_inf = pr.get_lamp_info()                           # Запросили инфу о лампах
        if res:
            print('Lamp1. State: %d. time: %d' % (lmp_inf[0][1], lmp_inf[0][0])) 
            print('Lamp2. State: %d. time: %d' % (lmp_inf[1][1], lmp_inf[1][0])) 
    
    
   
"""


class ErrCode:
    ERROR = -1
    OK = 0
    TCP_PROBLEM = 0x01      # for some reasons size of send data is less than required
    TCP_NOCONN = 0x02       # unable to connect
    TCP_CONNABORTED = 0x03  # after 30s of silence projector finished tcp session
    PJ_WRONGPASS = 0x04     # projector requires password or you send wrong pass
    PJ_NOANSWER = 0x10      # no answer on pj command - receive buffer is empty
    PJ_UNKANSWER = 0x15     # unable to parse receive data - projector send smth unexpected
    # PJ lin standard errors
    PJ_ERR1 = 0x11          # Undefined CMD
    PJ_ERR2 = 0x12          # Out of parameter
    PJ_ERR3 = 0x13          # Unavailable time
    PJ_ERR4 = 0x14          # unknown Failure


class Projector:
    def __init__(self, ip: str):
        self.__ip = ip
        self.__port = 4352
        self.__socket = socket.socket()
        self.__socket.settimeout(30)
        self.__err_code = ErrCode.OK

    # ------------- public --------------------------
    def getlasterror(self):
        """
        :return: error code
        """
        return self.__err_code


    def open_connection(self):
        """
         Open TCP session without authentication procedure.
         :return True/False
         """
        self.__err_code = ErrCode.OK

        if self.__socket.connect_ex((self.__ip, self.__port)) != 0:     # открываем сессию
            self.__socket.close()
            self.__err_code = ErrCode.TCP_NOCONN
            return False

        result, answer = self.__cmd_receive('PJLINK ')                  # ожидаем от проектора команду
        if result != ErrCode.OK:                                        # 'PJLINK' с индентификатором
            return False                                                # пароля

        if answer[0] == '0':                                            # Пароль не требуется
            self.__err_code = ErrCode.OK
        elif answer[0] == '1':                                          # Нужен пароль
            self.__err_code = ErrCode.PJ_WRONGPASS
        else:
            self.__err_code = ErrCode.ERROR                             # получили что-то неожиданное

        if self.__err_code == ErrCode.OK:
            return True
        else:
            return False

    def close_connection(self):
        self.__socket.close()

    def set_power(self, key: int):
        """
        Power On/Off the projector
        :param key: 0 - power off, 1 - power on
        :return: True/False
        """
        if self.__set_pjcmd('POWR', {0: '0', 1: '1'}, key) != ErrCode.OK:
            return False
        return True

    def set_shutter(self, key: int):
        """
        Open/Close shutter
        :param key: 0 - open shutter, 1 - close
        :return: True/False
        """
        if self.__set_pjcmd('AVMT', {0: '30', 1: '31'}, key) != ErrCode.OK:
            return False
        return True

    def set_input(self, key: int):
        """
        Set projector input: RGB, HDMI, DVI...
        If unsupported input is selected  projector will return PJ_ERR2 code
        check 'get_avail_inputs()' method
        :param key: channel number(check spec. on INPT cmd)
        :return: True/False
        """
        inpts = {a: a for a in range(11, 60) if a % 10 != 0}
        if self.__set_pjcmd('INPT', inpts, key) != ErrCode.OK:
            return False
        return True

    #  Get functions
    def get_power_stat(self):
        """
        Get power state of projector
        :return: True and code(0:'OFF', 1:'ON', 2:'COOLING', 3: 'WARM UP')
                 False and -1
        """
        result, answer = self.__get_pjcmd('POWR')
        if result != ErrCode.OK:
            return False, -1
        return True, int(answer[0])

    def get_lamp_info(self):
        """
        Get lamp info: [lamp1_inf, lamp2_inf,...,lamp8_inf]. 8 - max
        lamp[i]_inf: [t, st] where t - time in hours and st - 0:Off, 1:On
        :return: True and lamp_inf/False and empty list
        """
        result, answer = self.__get_pjcmd('LAMP')
        if result != ErrCode.OK:
            return False, {}
                                                        # парснг ответа
        answer = answer.replace('\r', ' ', 1)           # избавляемся от знака возврата каретки
        lamp_list = answer.split(sep=' ', maxsplit=15)  # разбиваем по пробелам
        lamp_list.pop()
        lamps_val = [int(item) for item in lamp_list]   # переводим в числа
        lamps_inf = []
        for i in range(0, len(lamps_val)//2):           # группируем по 2, для каждой лампы
            lamps_inf.append(lamps_val[2*i:2*i+2])
        return True, lamps_inf

    # return code.
    def get_shutter_state(self):
        """
        Get shutter state: 0:'MUTE OFF', 1:'MUTE ON'
        :return: true and state/false and -1
        """
        result, answer = self.__get_pjcmd('AVMT')
        if result != ErrCode.OK:
            return False, -1
        return True, int(answer[1])

    def get_input(self):
        """
        Get current projector input(check spec. on INPT cmd)
        :return: true and input value/false and -1
        """
        result, answer = self.__get_pjcmd('INPT')
        if result != ErrCode.OK:
            return False, -1
        return True, int(answer[0:2])

    def get_avail_inputs(self):
        """
        get available inputs for current projector
        returned values could be used in set_inputs() method
        :return: true and inputs_codes/false and empty list
        """
        result, answer = self.__get_pjcmd('INST')
        if result != ErrCode.OK:
            return False, []

        answer = answer.replace('\r', ' ', 1)
        inplist = answer.split(sep=' ', maxsplit=15)
        inplist.pop()
        inputs = [int(item) for item in inplist]
        return True, inputs

    def get_pjerror(self):
        """
        get projector errors: [Fan, Lamp, Temp, Cover, Filter, Other]
         0 - Ok, 1 - warning, 2 - Error
        :return: true and list of errors/false and empty list
        """
        result, answer = self.__get_pjcmd('ERST')
        if result != ErrCode.OK:
            return False, []

        err_list = []
        for s in answer[:-1]:
            err_list.append(int(s))
        return True, err_list

    def get_class(self):
        """
        get projector pjlink class
        :return: true and class val/false and -1
        """
        result, answer = self.__get_pjcmd('CLSS')
        if result != ErrCode.OK:
            return False, -1
        return True, int(answer[0])

    def show_prj_info(self):
        """
        get projector names - network name, manufacture, model
        :return: string wih names/empty if all command failed
        """
        cmds = ['NAME', 'INF1', 'INF2', 'INF0']
        answer = ['', '', '', '']
        prjname = str()
        for i in range(0, 4):
            result, answer[i] = self.__get_pjcmd(cmds[i])
            if result != ErrCode.OK:
                print('%s error: 0x%x' % (cmds[i], result))
            else:
                answer[i] = answer[i].replace('\r', '', 1)
                prjname = prjname + answer[i] + ' '  # answer[0] + ':' + ' ' + answer[1] + ' ' + answer[2]
        return prjname

    # ------------- local  --------------------------
    def __cmd_send(self, command):
        """
        send command to projector
        :param command: string - pj link command(check PJlink spec. for cmd format)
        :return: error code
        """
        self.__err_code = ErrCode.OK

        try:
            if self.__socket.send(command.encode('utf-8')) != len(command):     # отправляем команду. Метод сокета
                self.__err_code = ErrCode.TCP_PROBLEM                           # возвращете кол-во переданных данных
                self.__socket.close()                                           # возвращаем ошибку если не совпали

        except ConnectionAbortedError:                                          # обрабатываем исключение, если мы
            print('WARN: May be projector aborted connection')                  # долго ждали и проектор закрыл
            self.__err_code = ErrCode.TCP_CONNABORTED                           # соединение
            self.__socket.close()

        return self.__err_code

    def __cmd_receive(self, pattern: str):
        """
        Receive projector response to executed command
        :param pattern: projector response has to contain this patter(check PjLink spec)
        :return: error code
        """
        self.__err_code = ErrCode.OK
        start = time.time()
        while 1:
            buff = self.__socket.recv(1024).decode("utf-8")     # принимаем данные
            if buff:                                            # если что-то пришло
                buff_parse = buff.partition(pattern)            # ищем паттерн
                if buff_parse[1]:                               # если совпал
                    return self.__err_code, buff_parse[2]       # возврашаем OK и параметры ответа

            if time.time() - start > 30:
                if buff:                                        # если через 30 секунд ответа не нашли, но что то
                    self.__err_code = ErrCode.PJ_UNKANSWER      # приняли от проектора
                else:
                    self.__err_code = ErrCode.PJ_NOANSWER       # если за 30 секунд ничего не пришло
                self.__socket.close()
                break

        return self.__err_code, ''

    def __parse_pjerror_answer(self, answer: str):
        """
        Parse projector answer on standard pj link errors
        :param answer: string
        :return: error code
        """
        if 'ERR1' in answer:
            self.__err_code = ErrCode.PJ_ERR1
        elif 'ERR2' in answer:
            self.__err_code = ErrCode.PJ_ERR2
        elif 'ERR3' in answer:
            self.__err_code = ErrCode.PJ_ERR3
        elif 'ERR4' in answer:
            self.__err_code = ErrCode.PJ_ERR4
        else:
            self.__err_code = ErrCode.OK
        return self.__err_code

    def __ex_cmd(self, cmd_name: str, arg: str):
        """
        Execute PJ link command
        :param cmd_name: cmd name
        :param arg: cmd argument
        :return: error code and answer
        """
        cmd = '%%1%4s %s\r' % (cmd_name, arg)           # cmd format
        rec_pattern = '%%1%4s=' % cmd_name              # expected response header

        result = self.__cmd_send(cmd)
        if result != ErrCode.OK:
            return result, ''

        result, answer = self.__cmd_receive(rec_pattern)
        if result != ErrCode.OK:
            return result, ''

        result = self.__parse_pjerror_answer(answer)
        if result != ErrCode.OK:
            return result, ''

        return result, answer

    def __set_pjcmd(self, cmd_name: str, key_spec: dict, key: int):
        """
        Generalized set command
        :param cmd_name:    command name
        :param key_spec:    supported parameters values
        :param key:         selected parameter
        :return: error code
        """
        result, answer = self.__ex_cmd(cmd_name, key_spec[key])
        # if result != ErrCode.OK:
            # print('set_pjcmd error: 0x%x' % self.__err_code)
        return result

    def __get_pjcmd(self, cmd_name: str):
        """
        Generalized get command
        :param cmd_name: command name
        :return: error code and projector response
        """
        result, answer = self.__ex_cmd(cmd_name, '?')
        # if result != ErrCode.OK:
            # print('get_pjcmd error: 0x%x' % self.__err_code)
        return result, answer


