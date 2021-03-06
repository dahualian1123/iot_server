#!/usr/bin/env python
#-*- coding:utf-8 -*-

import socket
import select
import os
from common import gl

filename=os.path.basename(os.path.realpath(__file__))

class my_epoll():
    def __init__(self,ip,port,timeout):
        #超时时间
        self.timeout = timeout

        #创建socket对象
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #设置IP地址复用
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #ip地址和端口号
        server_address = (ip, port)
        #绑定IP地址
        self.serversocket.bind(server_address)
        #监听，并设置最大连接数
        self.serversocket.listen(self.timeout)
        print("服务器启动成功，监听IP：" , server_address)
        #服务端设置非阻塞
        self.serversocket.setblocking(False)  
        #创建self.epoll事件对象，后续要监控的事件添加到其中
        self.epoll = select.epoll()
        #注册服务器监听fd到等待读事件集合
        self.epoll.register(self.serversocket.fileno(), select.EPOLLIN)
        #文件句柄到所对应对象的字典，格式为{句柄：对象}
        #gl.fd_to_socket = {self.serversocket.fileno():self.serversocket,}        
        gl.fd_to_socket[self.serversocket.fileno()] =self.serversocket
    
    '''def send_event(self):
        for fd,socket in gl.fd_to_socket.items():
            print(fd,socket)
            if (socket != self.serversocket):
                print("%"*20)
                socket.send("1234567890我的".encode('gbk'))'''
        
    def run(self,parseHandler):
        print("*"*50)
        while True:
            gl.log.debug(filename+"-waitting for active conection......")
            #轮询注册的事件集合，返回值为[(文件句柄，对应的事件)，(...),....]
            events = self.epoll.poll(self.timeout)
            if not events:
                gl.log.debug(filename+"-self.epoll timeout,rewait......")
                continue
            gl.log.debug(filename+"-have{} new event，parse......".format(len(events)))

            for fd, event in events:
                socket = gl.fd_to_socket[fd]
                #如果活动socket为当前服务器socket，表示有新连接
                if socket == self.serversocket:
                    connection, address = self.serversocket.accept()
                    print("新连接：" , address)
                    #新连接socket设置为非阻塞
                    connection.setblocking(False)
                    #注册新连接fd到待读事件集合
                    self.epoll.register(connection.fileno(), select.EPOLLIN)
                    #把新连接的文件句柄以及对象保存到字典
                    gl.fd_to_socket[connection.fileno()] = connection
                    #以新连接的对象为键值，值存储在队列中，保存每个连接的信息
                    #gl.message_queues[connection]  = queue.Queue()
                #关闭事件
                elif (event & select.EPOLLHUP):
                    print('client close')
                    #在self.epoll中注销客户端的文件句柄
                    self.epoll.unregister(fd)
                    #关闭客户端的文件句柄
                    gl.fd_to_socket[fd].close()
                    #在字典中删除与已关闭客户端相关的信息
                    del gl.fd_to_socket[fd]
                #可读事件
                elif event & select.EPOLLIN:
                    #接收数据
                    data = socket.recv(1024)
                    if data:
                        print("收到数据：" , data , "客户端：" , socket.getpeername())
                        gl.executor_e.submit(parseHandler,({'fd':fd,'data':data}))
                        #parseHandler({'fd':fd,'data':data})
                        #将数据放入对应客户端的字典
                        #gl.message_queues[socket].put(data)
                        #修改读取到消息的连接到等待写事件集合(即对应客户端收到消息后，再将其fd修改并加入写事件集合)
                        #self.epoll.modify(fd, select.EPOLLOUT)
                    else:
                        print('client close')
                        #在self.epoll中注销客户端的文件句柄
                        self.epoll.unregister(fd)
                        #关闭客户端的文件句柄
                        gl.fd_to_socket[fd].close()
                        #在字典中删除与已关闭客户端相关的信息
                        del gl.fd_to_socket[fd]
                #可写事件
                '''elif event & select.EPOLLOUT:
                    try:
                        print("^"*50)
                        print(gl.message_queues)
                        #从字典中获取对应客户端的信息
                        msg = gl.message_queues[socket].get_nowait()
                    except queue.Empty:
                        print(socket.getpeername() , " queue empty")
                        #修改文件句柄为读事件
                        self.epoll.modify(fd, select.EPOLLIN)
                    else :
                        print("发送数据：" , data , "客户端：" , socket.getpeername())
                        #发送数据
                        socket.send(msg)'''

        #在self.epoll中注销服务端文件句柄
        self.epoll.unregister(self.serversocket.fileno())
        #关闭self.epoll
        self.epoll.close()
        #关闭服务器socket
        self.serversocket.close()
