import java.rmi.Remote;
import java.rmi.RemoteException;
import java.util.List;

/**
 * Interfaz remota para el servicio de logging centralizado
 */
public interface LoggingService extends Remote {
    
    /**
     * Registra una operación de inicio en el log
     * @param timestamp Tiempo de la operación
     * @param gameId Identificador del juego
     * @param operation Operación realizada
     * @param details Detalles adicionales de la operación
     * @throws RemoteException Error de comunicación RMI
     */
    void logStart(long timestamp, String gameId, String operation, String... details) throws RemoteException;
    
    /**
     * Registra una operación de finalización en el log
     * @param timestamp Tiempo de la operación
     * @param gameId Identificador del juego
     * @param operation Operación realizada
     * @param details Detalles adicionales de la operación
     * @throws RemoteException Error de comunicación RMI
     */
    void logEnd(long timestamp, String gameId, String operation, String... details) throws RemoteException;
    
    /**
     * Obtiene todos los logs registrados
     * @return Lista de todas las entradas de log
     * @throws RemoteException Error de comunicación RMI
     */
    List<String> getAllLogs() throws RemoteException;
    
    /**
     * Obtiene los logs de un juego específico
     * @param gameId Identificador del juego
     * @return Lista de logs del juego especificado
     * @throws RemoteException Error de comunicación RMI
     */
    List<String> getGameLogs(String gameId) throws RemoteException;
    
    /**
     * Limpia todos los logs
     * @throws RemoteException Error de comunicación RMI
     */
    void clearLogs() throws RemoteException;
}
