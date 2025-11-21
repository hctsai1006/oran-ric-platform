import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface BeamKPI {
  beam_id: number;
  cell_id: string;
  ue_count: number;
  timestamp: string;
  kpis: {
    signal_quality: {
      rsrp: number;
      rsrq: number;
      sinr: number;
    };
    throughput: {
      dl_throughput_mbps: number;
      ul_throughput_mbps: number;
    };
    resource: {
      prb_usage_dl: number;
      prb_usage_ul: number;
    };
    latency: {
      packet_delay_ms: number;
      rtt_ms: number;
    };
    error: {
      packet_loss_rate: number;
      bler: number;
    };
  };
}

export interface KPIQuery {
  beam_id: number;
  kpi_type?: string;
  time_range?: string;
}

@Injectable({
  providedIn: 'root'
})
export class KpiService {
  private apiUrl = '/api/kpimon';  // Will be proxied to KPIMON xApp

  constructor(private http: HttpClient) { }

  // Get KPI for specific beam
  getBeamKPI(beam_id: number, kpi_type: string = 'all', time_range: string = 'current'): Observable<BeamKPI> {
    return this.http.get<BeamKPI>(
      `${this.apiUrl}/beam/${beam_id}/kpi?kpi_type=${kpi_type}&time_range=${time_range}`
    );
  }

  // Get KPI for all beams
  getAllBeamsKPI(): Observable<BeamKPI[]> {
    const beams: Observable<BeamKPI>[] = [];
    for (let i = 1; i <= 7; i++) {
      beams.push(this.getBeamKPI(i));
    }
    return new Observable(observer => {
      Promise.all(beams.map(b => b.toPromise())).then(results => {
        observer.next(results as BeamKPI[]);
        observer.complete();
      });
    });
  }

  // Get historical KPI data
  getHistoricalKPI(beam_id: number, hours: number = 1): Observable<BeamKPI[]> {
    return this.http.get<BeamKPI[]>(
      `${this.apiUrl}/beam/${beam_id}/history?hours=${hours}`
    );
  }
}
