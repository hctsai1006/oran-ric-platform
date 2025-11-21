import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface XApp {
  name: string;
  namespace: string;
  status: string;
  replicas: number;
  ready_replicas: number;
  port?: number;
  version: string;
  metrics_port?: number;
  created?: string;
  health: {
    alive: boolean;
    ready: boolean;
    paths?: {
      rmr: { healthy: boolean; latency: number };
      http: { healthy: boolean; latency: number };
      active: string;
    };
  };
}

export interface XAppMetrics {
  messages_received: number;
  messages_processed: number;
  messages_failed: number;
  processing_time_avg: number;
}

@Injectable({
  providedIn: 'root'
})
export class XappService {
  private apiUrl = '/api';  // Will be proxied by nginx/kong

  constructor(private http: HttpClient) { }

  // Get all xApps status
  getXApps(): Observable<XApp[]> {
    return this.http.get<XApp[]>(`${this.apiUrl}/xapps`);
  }

  // Get specific xApp details
  getXApp(name: string): Observable<XApp> {
    return this.http.get<XApp>(`${this.apiUrl}/xapps/${name}`);
  }

  // Get xApp health status
  getXAppHealth(name: string, port: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/xapps/${name}/health`);
  }

  // Get xApp metrics
  getXAppMetrics(name: string): Observable<XAppMetrics> {
    return this.http.get<XAppMetrics>(`${this.apiUrl}/xapps/${name}/metrics`);
  }

  // Get xApp logs
  getXAppLogs(name: string, lines: number = 100): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/xapps/${name}/logs?lines=${lines}`);
  }

  // Restart xApp
  restartXApp(name: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/xapps/${name}/restart`, {});
  }

  // Scale xApp replicas
  scaleXApp(name: string, replicas: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/xapps/${name}/scale`, { replicas });
  }
}
