import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface PrometheusMetric {
  metric: { [key: string]: string };
  value: [number, string];
}

export interface PrometheusResponse {
  status: string;
  data: {
    resultType: string;
    result: PrometheusMetric[];
  };
}

@Injectable({
  providedIn: 'root'
})
export class PrometheusService {
  private apiUrl = '/api/prometheus';  // Will be proxied to Prometheus server

  constructor(private http: HttpClient) { }

  // Query Prometheus
  query(query: string): Observable<PrometheusMetric[]> {
    return this.http.get<PrometheusResponse>(
      `${this.apiUrl}/api/v1/query?query=${encodeURIComponent(query)}`
    ).pipe(
      map(response => response.data.result)
    );
  }

  // Query Prometheus range
  queryRange(query: string, start: number, end: number, step: string = '15s'): Observable<any> {
    return this.http.get(
      `${this.apiUrl}/api/v1/query_range?query=${encodeURIComponent(query)}&start=${start}&end=${end}&step=${step}`
    );
  }

  // Get xApp metrics
  getXAppMetrics(xapp_name: string): Observable<any> {
    return this.query(`{app="${xapp_name}"}`);
  }

  // Get dual-path metrics
  getDualPathMetrics(): Observable<any> {
    return this.query('dual_path_active_path');
  }

  // Get message processing rate
  getMessageRate(xapp_name: string): Observable<number> {
    return this.query(`rate(${xapp_name}_messages_received_total[5m])`).pipe(
      map(result => result.length > 0 ? parseFloat(result[0].value[1]) : 0)
    );
  }

  // Get active alerts
  getActiveAlerts(): Observable<any> {
    return this.http.get(`${this.apiUrl}/api/v1/alerts`);
  }
}
