import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.util.Arrays;

public class Client {

    private static final int PORT = 4001;
    public static void main(String [] args){



        try{
            int[][] a = { { 1, 2, -3 }, { 4, 0, -2 } };
            int[][] b = { { 3, 1 }, { 2, 4 }, { -1, 5 } };
            

            Registry registry = LocateRegistry.getRegistry("127.0.0.1",PORT);
            CalcMatrix calMatImp = (CalcMatrix) registry.lookup("Calculadora");


            int[][] c = calMatImp.multiply(a, b);

            System.out.println("matrix A =>  "+Arrays.deepToString(a));
            System.out.println("matrix B =>  "+Arrays.deepToString(b));
            System.out.println("matrix AxB =>  "+Arrays.deepToString(c));
        
        } catch(Exception e){
            System.err.println("Calculator Excepcion :");
            e.printStackTrace();
            System.exit(1);
        }

    }
}
