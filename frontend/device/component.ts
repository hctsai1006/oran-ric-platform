// Copyright 2017 The Kubernetes Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import {Component, Inject} from '@angular/core';
import {VersionInfo} from '@api/root.ui';
import {AssetsService} from '@common/services/global/assets';
import {ConfigService} from '@common/services/global/config';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'kd-about',
  templateUrl: './template.html',
  styleUrls: ['./style.scss'],
})
export class AboutComponent {
  latestCopyrightYear: number;
  versionInfo: VersionInfo;
  apiRoot = "http://192.168.50.12:8000";
  deviceConfig: [];
  deviceHealth: Array<string>;
  deviceDetails: Array<{}>;
  isDetailsShow: Boolean;
  showingDetails: {};

  constructor(@Inject(AssetsService) public assets: AssetsService, config: ConfigService, private http: HttpClient) {
    this.versionInfo = config.getVersionInfo();
    this.latestCopyrightYear = new Date().getFullYear();
  }

  ngOnInit() {
    this.http.get<[]>(this.apiRoot + "/catalog").subscribe((data) => {
      this.deviceConfig = data;
      console.log(this.deviceConfig);
      this.deviceHealth = new Array(this.deviceConfig.length);
      this.deviceDetails = new Array(this.deviceConfig.length);
      for(let i=0; i<this.deviceConfig.length; i++) {
        this.sendDataRequest(i);
      }
    })
  }

  
  sendConfigRequest() {
    let name: string = (<HTMLInputElement>document.getElementById("device-name")).value;
    let ip: string = (<HTMLInputElement>document.getElementById("device-ip")).value;
    let port: number = Number.parseInt((<HTMLInputElement>document.getElementById("device-port")).value);
    let username: string = (<HTMLInputElement>document.getElementById("device-username")).value;
    let password: string = (<HTMLInputElement>document.getElementById("device-password")).value;

    console.log({
      "name": name,
      "host": ip,
      "username": username,
      "password": password,
      "xpath": "",
      "port": port
    });
    
    this.http.post(this.apiRoot + "/config/add", {
      "name": name,
      "host": ip,
      "username": username,
      "password": password,
      "xpath": "",
      "port": port
    }).subscribe(
      (data) => {
        console.log(data);
        location.reload();
      }
    )
  }

  sendDataRequest(index: number){
    this.http.get<{}>(this.apiRoot + "/data/" + index.toString()).subscribe((data) => {
      console.log("data", data);
      if(data !== null) {
        this.deviceHealth[index] = "Alive";
        console.log(this.deviceHealth[index]);
        this.deviceDetails[index] = JSON.parse(JSON.stringify(data))['data']['netconf-state']['capabilities']['capability'];
      }else{
        this.deviceHealth[index] = "Leave";
        console.log(this.deviceHealth[index]);
      }
    });
  }

  deleteConfig(index: number) {
    if(confirm("Sure to delete?")) {
      this.http.get(this.apiRoot + "/config/delete/" + index.toString()).subscribe((data) => {
        console.log(data);
        location.reload();
      })
    }
  }
  
  showCapability(index: number) {
    if(this.isDetailsShow) {
      this.isDetailsShow = !this.isDetailsShow;
    } else {
      this.isDetailsShow = true;
      this.showingDetails = this.deviceDetails[index];

      console.log(this.showingDetails);
    }
  }
}
