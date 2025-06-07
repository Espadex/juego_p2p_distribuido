
Para ejecutar este sistema debe

1) crear los .class de caha ejemplo creado en java, puede hacerlo ejecutando.

```
cd appServer
javac Cliente.java
javac ClienteImp.java
javac ServicioChat.java
javac ServicioChatImp.java
javac ServidorChat.java

cd ..
cd appClient
javac ClienteChat.java
```

2) copiar appServer/cliente.class, appServer/clienteImp.class y appServer/ServicioChat.class a appClient


3) abrir 4 consolas

4) en consola(1) debe ejecutar el siguiente comando, el cual habilita la escucha del puerto 4002 (para este ejemplo) para RMI. Esto debe realizarlo en el servidor.

linux
```
 cd appServer
rmiregistry 4002
```

Windows
```
 cd appServer
rmiregistry.exe 4002
```
5) en consola(2) ejecutar

```
cd appServer
java ServidorChat
```

6) en la consola(3) ejecutar el cliente del chat, ingresar tu apodo y luego enviar mensajes

```
cd appClient
java ClienteChat luis
```
6) en la consola(4) ejecutar el cliente del chat, ingresar tu apodo y luego enviar mensajes

```
cd appClient
java ClienteChat maria
```

Nota: en este caso particular puede generar tantas instancias de "java ClienteChat xxxx" como participantes en el chat quiera simular