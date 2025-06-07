import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;

/**
 * Implementación del servicio de logging centralizado
 */
public class LoggingServiceImpl extends UnicastRemoteObject implements LoggingService {
    
    private final List<String> logs;
    private final String logFileName;
    private final SimpleDateFormat dateFormat;
    
    public LoggingServiceImpl() throws RemoteException {
        super();
        this.logs = new CopyOnWriteArrayList<>();
        this.logFileName = "game_logs.txt";
        this.dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
        
        // Log de inicio del servidor
        logToFile("=== SERVIDOR DE LOGS INICIADO ===");
        System.out.println("Servidor de logging centralizado iniciado");
    }
    
    @Override
    public void logStart(long timestamp, String gameId, String operation, String... details) throws RemoteException {
        String logEntry = formatLogEntry(timestamp, "ini", gameId, operation, details);
        addLog(logEntry);
    }
    
    @Override
    public void logEnd(long timestamp, String gameId, String operation, String... details) throws RemoteException {
        String logEntry = formatLogEntry(timestamp, "fin", gameId, operation, details);
        addLog(logEntry);
    }
    
    @Override
    public List<String> getAllLogs() throws RemoteException {
        return new ArrayList<>(logs);
    }
    
    @Override
    public List<String> getGameLogs(String gameId) throws RemoteException {
        List<String> gameLogs = new ArrayList<>();
        for (String log : logs) {
            if (log.contains(gameId)) {
                gameLogs.add(log);
            }
        }
        return gameLogs;
    }
    
    @Override
    public void clearLogs() throws RemoteException {
        logs.clear();
        logToFile("=== LOGS LIMPIADOS ===");
        System.out.println("Logs limpiados");
    }
    
    private String formatLogEntry(long timestamp, String type, String gameId, String operation, String... details) {
        StringBuilder sb = new StringBuilder();
        sb.append("timestamp(").append(timestamp).append("), ");
        sb.append(type).append(", ");
        sb.append(gameId).append(", ");
        sb.append(operation);
        
        for (String detail : details) {
            if (detail != null && !detail.trim().isEmpty()) {
                sb.append(", ").append(detail);
            }
        }
        
        return sb.toString();
    }
    
    private void addLog(String logEntry) {
        // Agregar timestamp legible al log
        String timestampedEntry = "[" + dateFormat.format(new Date()) + "] " + logEntry;
        
        logs.add(timestampedEntry);
        logToFile(timestampedEntry);
        
        System.out.println("LOG: " + timestampedEntry);
    }
    
    private void logToFile(String logEntry) {
        try (FileWriter writer = new FileWriter(logFileName, true)) {
            writer.write(logEntry + "\n");
            writer.flush();
        } catch (IOException e) {
            System.err.println("Error escribiendo al archivo de log: " + e.getMessage());
        }
    }
}
