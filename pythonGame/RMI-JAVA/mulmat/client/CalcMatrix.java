import java.rmi.Remote; 
import java.rmi.RemoteException; 

public interface CalcMatrix extends Remote {

    public int[][] multiply(int[][] a, int[][] b) throws RemoteException;
    
}
