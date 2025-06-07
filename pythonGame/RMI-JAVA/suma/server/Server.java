import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.rmi.server.UnicastRemoteObject;


class Server {

    private static final int PORT = 4000;
    public static void main(String[] args) {
        
        try{
            System.setProperty("java.rmi.server.hostname","127.0.0.1");
            
            CalculatorImp calImp = new CalculatorImp();
            Calculator stub =(Calculator) UnicastRemoteObject.exportObject(calImp,0);


            Registry registry = LocateRegistry.getRegistry("127.0.0.1",PORT);
            System.out.println("Servidor escuchando en el puerto " + String.valueOf(PORT));
            registry.bind("Calculadora", stub);
            //Naming.rebind("rmi://localhost:" + PORT + "/Eco", calImp);
        }
        catch (RemoteException e) {
            System.err.println("Comunication Error: " + e.toString());
            System.exit(1);
        }
        catch (Exception e) {
            System.err.println("Calculator Excepcion :");
            e.printStackTrace();
            System.exit(1);
        }

    }
}