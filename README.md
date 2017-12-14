# PJlink-
API to communicate with projectors through pj-link protocol
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
