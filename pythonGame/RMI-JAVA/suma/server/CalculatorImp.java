import java.rmi.RemoteException;

public class CalculatorImp implements Calculator {

    @Override
    public float sum(float a, float b) throws RemoteException {
        // TODO Auto-generated method stub
        return a+b;
    }

}
