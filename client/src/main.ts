import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { environment } from './environments/environment';

if (environment.production) {
  // Guarda una referencia a console.error ya que lo quieres mantener
  const originalError = console.error;

  // Reemplazar los métodos de console con funciones vacías
  console.log = () => {};
  console.info = () => {};
  console.debug = () => {};
  console.warn = () => {};

  // Conservar console.error
  console.error = originalError;
}

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));
