Para ejecutar este sistema debe

1) crear los .class de caha ejemplo creado en java, puede hacerlo ejecutando.

```
cd server
javac Calculator.java
javac CalculatorImp.java
javac Server.java

cd ..
cd client
javac Calculator.java
javac Client.java
```


2) abrir 3 consolas

3) en una de las consolas debe ejecutar el siguiente comando, el cual habilita la escucha del puerto 4000 (para este ejemplo) para RMI. Esto debe realizarlo en el servidor.

linux
```
 cd server
rmiregistry 4000
```

Windows
```
rmiregistry.exe 4000
```
4) en la segunda consola ejecutar el servidor

```
cd server
java Server
```

5) en la tercera consola ejecutar el cliente, debe pasar dos argumentos númericos

```
cd client
java Client 1.1 2.5
```
