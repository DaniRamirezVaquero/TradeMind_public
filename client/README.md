# TradeMind Frontend 📱💹

## Descripción del Proyecto 📚
La interfaz de usuario de TradeMind proporciona una experiencia interactiva para la compra-venta de smartphones. Desarrollada en Angular, ofrece una interfaz moderna y responsiva para interactuar con nuestro sistema de agentes inteligentes através de un chat.

## Características Principales 🌟

### Chat Interactivo 💬
- Interfaz de chat en tiempo real
- Soporte para diferentes tipos de mensajes:
  - Texto plano
  - Gráficos de precios
  - Recomendaciones estructuradas
- Historial de conversación persistente
- Indicadores de estado de escritura

### Visualización de Datos 📊
- Gráficos interactivos de precios
- Visualización de tendencias temporales
- Comparativas de dispositivos
- Filtros dinámicos

### Características de UX 🎨
- Diseño responsivo
- Animaciones fluidas
- Accesibilidad mejorada

## Estructura del Proyecto 📁

```
client/
├── src/
│   ├── app/
│   │   ├── components/     # Componentes reutilizables
│   │   ├── services/       # Servicios de la aplicación
│   │   ├── interfaces/     # Interfaces y tipos
├── angular.json         # Configuración de Angular
└── package.json         # Dependencias
```

## Requisitos Previos 📋
- Node.js 16+
- Angular CLI 16+
- Conexión al backend de TradeMind*

## Configuración del Entorno 🔧

1. Clona el repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd TradeMind/client
   ```

2. Instala las dependencias:
   ```bash
   npm install
   ```

3. Configura las variables de entorno:
   - Copia `environment.example.ts` a `environment.ts`
   - Ajusta la URL del backend según sea necesario

## Comandos Disponibles 🛠️

```bash
# Desarrollo
ng serve               # Inicia servidor de desarrollo
ng serve --port 4200   # Especifica puerto

# Construcción
ng build              # Construye para producción
ng build --prod       # Construcción optimizada

# Generación de código
ng generate component nombre-componente
ng generate service nombre-servicio
ng generate pipe nombre-pipe
```

## Comunicación con el Backend 🔌

### Endpoints Utilizados
- `POST /chat` - Envío de mensajes
- `POST /init-session` - Inicio de sesión
- `GET /messages/{session_id}` - Recuperación de historial

### Ejemplo de Uso del Servicio de Chat
```typescript
this.chatService.sendMessage({
  content: 'mensaje',
  type: 'text',
  sessionId: 'session-123'
}).subscribe(response => {
  console.log(response);
});
```

## Estado del Desarrollo 🚧
- [x] Interfaz básica de chat
- [x] Integración con backend
- [x] Visualización de gráficos
- [x] Gestión de sesiones
- [x] Responsive design
- [ ] PWA support
- [ ] Internacionalización
