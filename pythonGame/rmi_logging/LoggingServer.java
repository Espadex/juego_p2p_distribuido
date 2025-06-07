import java.rmi.Naming;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

/**
 * Servidor RMI para el servicio de logging centralizado
 */
public class LoggingServer {
    
    public static void main(String[] args) {
        try {
            // Crear y registrar el servicio de logging
            LoggingServiceImpl loggingService = new LoggingServiceImpl();
            
            // Iniciar el registro RMI en el puerto 1099
            try {
                Registry registry = LocateRegistry.createRegistry(1099);
                System.out.println("Registro RMI creado en puerto 1099");
            } catch (Exception e) {
                System.out.println("Registro RMI ya existe en puerto 1099");
            }
            
            // Registrar el servicio en el registro
            Naming.rebind("//localhost:1099/LoggingService", loggingService);
            
            System.out.println("=".repeat(50));
            System.out.println("🚀 SERVIDOR DE LOGGING CENTRALIZADO INICIADO");
            System.out.println("=".repeat(50));
            System.out.println("📍 Dirección: //localhost:1099/LoggingService");
            System.out.println("📁 Archivo de logs: game_logs.txt");
            System.out.println("⏰ Esperando conexiones de clientes...");
            System.out.println("=".repeat(50));
            
            // Mantener el servidor corriendo
            while (true) {
                Thread.sleep(1000);
            }
            
        } catch (Exception e) {
            System.err.println("Error en el servidor de logging: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
