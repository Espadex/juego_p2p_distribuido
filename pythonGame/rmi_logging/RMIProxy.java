import java.io.*;
import java.net.*;
import java.rmi.Naming;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonArray;

/**
 * Proxy que convierte conexiones TCP en llamadas RMI
 * Permite a los clientes Python comunicarse con el servidor RMI Java
 */
public class RMIProxy {
    
    private static final int PROXY_PORT = 25334;
    private LoggingService loggingService;
    private ServerSocket serverSocket;
    private ExecutorService threadPool;
    private boolean running = false;
    private Gson gson = new Gson();
    
    public RMIProxy() {
        this.threadPool = Executors.newFixedThreadPool(10);
    }
    
    public void start() {
        try {
            // Conectar al servicio RMI de logging
            loggingService = (LoggingService) Naming.lookup("//localhost:1099/LoggingService");
            System.out.println("✅ Conectado al servicio RMI de logging");
            
            // Iniciar servidor proxy
            serverSocket = new ServerSocket(PROXY_PORT);
            running = true;
            
            System.out.println("=".repeat(50));
            System.out.println("🔗 PROXY RMI INICIADO");
            System.out.println("=".repeat(50));
            System.out.println("📍 Puerto: " + PROXY_PORT);
            System.out.println("🎯 Conectado a: //localhost:1099/LoggingService");
            System.out.println("⏰ Esperando clientes Python...");
            System.out.println("=".repeat(50));
            
            while (running) {
                try {
                    Socket clientSocket = serverSocket.accept();
                    System.out.println("🔌 Cliente conectado: " + clientSocket.getRemoteSocketAddress());
                    
                    // Manejar cliente en hilo separado
                    threadPool.submit(new ClientHandler(clientSocket));
                    
                } catch (IOException e) {
                    if (running) {
                        System.err.println("Error aceptando conexión: " + e.getMessage());
                    }
                }
            }
            
        } catch (Exception e) {
            System.err.println("Error iniciando proxy RMI: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    public void stop() {
        running = false;
        try {
            if (serverSocket != null) {
                serverSocket.close();
            }
            threadPool.shutdown();
            System.out.println("🛑 Proxy RMI detenido");
        } catch (IOException e) {
            System.err.println("Error cerrando proxy: " + e.getMessage());
        }
    }
    
    private class ClientHandler implements Runnable {
        private Socket clientSocket;
        private BufferedReader reader;
        private PrintWriter writer;
        
        public ClientHandler(Socket socket) {
            this.clientSocket = socket;
        }
        
        @Override
        public void run() {
            try {
                reader = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
                writer = new PrintWriter(clientSocket.getOutputStream(), true);
                
                String line;
                while ((line = reader.readLine()) != null) {
                    try {
                        processRequest(line);
                    } catch (Exception e) {
                        System.err.println("Error procesando solicitud: " + e.getMessage());
                        writer.println("ERROR: " + e.getMessage());
                    }
                }
                
            } catch (IOException e) {
                System.out.println("🔌 Cliente desconectado: " + clientSocket.getRemoteSocketAddress());
            } finally {
                try {
                    if (reader != null) reader.close();
                    if (writer != null) writer.close();
                    clientSocket.close();
                } catch (IOException e) {
                    System.err.println("Error cerrando conexión: " + e.getMessage());
                }
            }
        }
        
        private void processRequest(String jsonRequest) {
            try {
                JsonObject request = gson.fromJson(jsonRequest, JsonObject.class);
                
                String method = request.get("method").getAsString();
                long timestamp = request.get("timestamp").getAsLong();
                String gameId = request.get("gameId").getAsString();
                String operation = request.get("operation").getAsString();
                
                // Convertir detalles a array de strings
                System.out.println("🔍 Método: " + method + ", GameId: " + gameId + ", Operation: " + operation);

                String[] details = new String[0];
                if (request.has("details") && !request.get("details").isJsonNull()) {
                    JsonArray detailsArray = request.getAsJsonArray("details");
                    details = new String[detailsArray.size()];
                    for (int i = 0; i < detailsArray.size(); i++) {
                        details[i] = detailsArray.get(i).getAsString();
                    }
                }
                
                // Llamar al método RMI correspondiente
                if ("logStart".equals(method)) {
                    System.out.println("🚀 Enviando logStart a RMI..."); 
                    loggingService.logStart(timestamp, gameId, operation, details);
                    writer.println("OK");
                    writer.flush();
                    System.out.println("✅ Log enviado correctamente: " + gameId + " - " + operation);
                } else if ("logEnd".equals(method)) {
                    System.out.println("🚀 Enviando logEnd a RMI...");
                    loggingService.logEnd(timestamp, gameId, operation, details);
                    writer.println("OK");
                    writer.flush(); // ← AGREGAR ESTO
                    System.out.println("✅ Log enviado correctamente: " + gameId + " - " + operation);
                } else {
                    System.out.println("❌ Método desconocido: " + method);
                    writer.println("ERROR: Método desconocido: " + method);
                    writer.flush();
                }
                
            } catch (Exception e) {
                System.err.println("❌ Error procesando solicitud JSON: " + e.getMessage());
                e.printStackTrace();
                writer.println("ERROR: " + e.getMessage());
                writer.flush();
            }
        }
    }
    
    public static void main(String[] args) {
        RMIProxy proxy = new RMIProxy();
        
        // Configurar shutdown hook
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("\n🛑 Cerrando proxy RMI...");
            proxy.stop();
        }));
        
        proxy.start();
    }
}
