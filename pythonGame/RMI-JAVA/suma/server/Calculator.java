import java.rmi.Remote; 
import java.rmi.RemoteException; 

public interface Calculator extends Remote {

    float sum(float a, float b) throws RemoteException;
    
}
