import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Dashboard {
  id: number;
  uid: string;
  title: string;
  uri: string;
  url: string;
  slug: string;
  type: string;
  tags: string[];
}

@Injectable({
  providedIn: 'root'
})
export class GrafanaService {
  private apiUrl = '/api/grafana';  // Will be proxied to Grafana server

  constructor(private http: HttpClient) { }

  // Get all dashboards
  getDashboards(): Observable<Dashboard[]> {
    return this.http.get<Dashboard[]>(`${this.apiUrl}/api/search?type=dash-db`);
  }

  // Get dashboard by UID
  getDashboard(uid: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/api/dashboards/uid/${uid}`);
  }

  // Get dashboard URL for embedding
  getDashboardEmbedUrl(uid: string, theme: string = 'dark', refresh: string = '5s'): string {
    return `${this.apiUrl}/d/${uid}?theme=${theme}&refresh=${refresh}&kiosk=tv`;
  }

  // Pre-defined dashboard UIDs
  getDashboardUids(): { [key: string]: string } {
    return {
      'platform-overview': 'oran-ric-overview',
      'kpimon': 'kpimon-dashboard',
      'traffic-steering': 'traffic-steering-dashboard',
      'qoe-predictor': 'qoe-predictor-dashboard',
      'ran-control': 'rc-xapp-dashboard',
      'federated-learning': 'federated-learning-dashboard',
      'dual-path': 'oran-dual-path'
    };
  }
}
