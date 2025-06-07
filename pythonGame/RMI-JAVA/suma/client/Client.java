import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class Client {

    private static final int PORT = 4000;
    public static void main(String [] args){

        float num1,num2;

        if (args.length!=2) {
            System.err.printf("debe usar 2 argumentos númericos(num1, num2), usted utilizó %d", args.length);
            return;
        }

        try{
            num1=Float.parseFloat(args[0]);
            num2=Float.parseFloat(args[1]);

            Registry registry = LocateRegistry.getRegistry("127.0.0.1",PORT);
            Calculator calImp = (Calculator) registry.lookup("Calculadora");

            System.out.printf("%f + %f = %f \n",num1, num2, calImp.sum(num1,num2));
        
        } catch(Exception e){
            System.err.println("Calculator Excepcion :");
            e.printStackTrace();
            System.exit(1);
        }

    }
}
