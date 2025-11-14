# Installation Guide of Kepler by Helm Chart
###### tags: `Install`
:::info
**Link**
* [Kepler](https://sustainable-computing.io/)
* [Kepler Source Code](https://github.com/sustainable-computing-io/kepler)
:::

## 1. Introduction 
[Kepler](https://hackmd.io/@Kenny-Lai/HyqGOKXr2)

## 2. Installation steps
:::warning
**Environment**
|    Ubuntu    |       Linux Kernel       |
|:------------:|:------------------------:|
| 20.04.6  LTS | 5.4.0-148-generic x86_64 |


| Kubernetes | k8s_cni_version |          Docker           | Helm  |
|:----------:|:---------------:|:-------------------------:|:-----:|
|  v1.16.0   |      0.7.5      | 20.10.12-0ubuntu1~20.04.1 | 3.5.4 |

:::

### 2-1 Add the helm repo
```shell=
helm repo add kepler https://sustainable-computing-io.github.io/kepler-helm-chart
helm repo list
```
![](https://hackmd.io/_uploads/HkxxI7rYh.png)

### 2-2 Install the Kepler
**Find the all versions available:**
```shell=
helm search repo kepler --versions
```
![](https://hackmd.io/_uploads/rJBCDmBtn.png)

**Install a specific chart version:**
```shell=
helm install kepler kepler/kepler --namespace kepler --create-namespace --version <CHART VERSION>
```
![](https://hackmd.io/_uploads/ryreu7rFh.png)


If you want to install the Kepler through override values.yaml file
```shell=
touch values.yaml
vim values.yaml
```
```yaml=
# version tag: kepler-0.4.1
---
# -- Replaces the name of the chart in the Chart.yaml file
nameOverride: ""
# -- Replaces the generated name
fullnameOverride: ""

image:
  # -- Repository to pull the image from
  repository: "quay.io/sustainable_computing_io/kepler"
  # -- Image tag, if empty it will get it from the chart's appVersion
  tag: ""
  # -- Pull policy
  pullPolicy: Always

# -- Secret name for pulling images from private repository
imagePullSecrets: []

# -- Additional DaemonSet annotations
annotations: {}

# -- Additional pod annotations
podAnnotations: {}

# -- Additional pod labels
podLabels: {}

# -- Privileges and access control settings for a Pod (all containers in a pod)
podSecurityContext: {}
  # fsGroup: 2000

# -- Privileges and access control settings for a container
securityContext:
  privileged: true

# -- Node selection constraint
nodeSelector:
  kubernetes.io/os: linux

# -- Toleration for taints
tolerations:
  - effect: NoSchedule
    key: node-role.kubernetes.io/control-plane

# -- Affinity rules
affinity: {}

# -- CPU/MEM resources
resources: {}

# -- Extra environment variables
extraEnvVars:
  KEPLER_LOG_LEVEL: "1"
  ENABLE_GPU: "true"
  ENABLE_EBPF_CGROUPID: "true"
  EXPOSE_IRQ_COUNTER_METRICS: "true"
  EXPOSE_KUBELET_METRICS: "true"
  ENABLE_PROCESS_METRICS: "true"
  CPU_ARCH_OVERRIDE: ""
  CGROUP_METRICS: "*"

service:
  annotations: {}
  type: ClusterIP
  port: 9102

serviceAccount:
  # Specifies whether a service account should be created
  create: true
  # Annotations to add to the service account
  annotations: {}
  # The name of the service account to use.
  # If not set and create is true, a name is generated using the fullname template
  name: ""

serviceMonitor:
  enabled: false
  namespace: ""
  interval: 30s
  scrapeTimeout: 5s
  labels: {}
```
```shell=
helm install kepler kepler/kepler --values values.yaml --namespace kepler --create-namespace
```
### 2-3 Check the Kelper API
```=
http://127.0.0.1:9102/metrics
```
### 2-4 Uninstall Kepler
```shell=
helm delete -n kepler kepler
```

## 3. Trouble Shooting
### 3-1 Error Log about bpf table
![](https://hackmd.io/_uploads/SyyiqmStn.png)
:::success
**Solution:**
I have checked with Kepler's developer, he think the message is benign, it doesn't stop kepler from reading ebpf maps. The root cause is that kepler uses batch ebpf map delete for efficiency. But this operation is not supported in older kernels.
:::


### 3-2 Error figures of metrics
Some value of metrics alway is 0. I think it is wrong.
Try to debug following the [Trouble Shooting of Kepler](https://sustainable-computing.io/usage/trouble_shooting/#:~:text=the%20MachineConfiguration%20here-,Kepler%20energy%20metrics%20are%20zeroes,-Background).
:::success
**Debug:**
```shell=
# Check system supports the version of cGroup 
grep cgroup /proc/filesystems
```
![](https://hackmd.io/_uploads/HJx_YDln3.png)
* If your system supports cgroup v2, you would see:
```
nodev   cgroup
nodev   cgroup2
```
* On a system with only cgroup v1, you would only see:
```
nodev   
cgroup
```


```shell=
# Identify the cgroup version on Linux Nodes 
stat -fc %T /sys/fs/cgroup/
```

![](https://hackmd.io/_uploads/rk9p32lhn.png)


* For cgroup v2, the output is `cgroup2fs`
* For cgroup v1, the output is `tmpfs`

```shell=
# enable cgroup v2 manually
echo 'GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT} systemd.unified_cgroup_hierarchy=1"' | sudo tee /etc/default/grub.d/70-cgroup-unified.cfg
sudo update-grub
sudo reboot -h now
```
![](https://hackmd.io/_uploads/HJ_Fa3lnh.png)

Identify the cgroup version again. 
![](https://hackmd.io/_uploads/HJx692g3n.png)

But kubelet service have some problems.
![](https://hackmd.io/_uploads/HyTn63xh3.png)
:::
:::warning
We meet the requirements of cgroup v2. We change the Ubuntu and Linux Kernel version.
![](https://hackmd.io/_uploads/SyAI9-z22.png)
:::


# Installation Guide of Kepler by Manifests
:::info
**Link**
* [Kepler](https://sustainable-computing.io/)
* [Kepler Source Code](https://github.com/sustainable-computing-io/kepler)
:::

## 1. Introduction 
[Kepler](/gDBxCOSFTEKJhE81sZ91Sw)



## 2. Installation steps
:::warning
**Environment**
|   Ubuntu    |       Linux Kernel       | 
|:-----------:|:------------------------:| 
| 22.04.3 LTS | 5.15.0-78-generic x86_64 | 

| Kubernetes | k8s_cni_version |          Docker           | Helm  |
|:----------:|:---------------:|:-------------------------:|:-----:|
|   1.21.0   |      0.7.5      | 20.10.21-0ubuntu1~22.04.3 | 3.5.4 |
:::
### 2-1 Git the Source Code
```shell=
git clone https://github.com/sustainable-computing-io/kepler.git
cd ~/kepler/
```

### 2-2 Build manifests
```shell=
make build-manifest OPTS="<deployment options>"
# minimum deployment: 
# > make build-manifest
# deployment with sidecar: 
# > make build-manifest OPTS="ESTIMATOR_SIDECAR_DEPLOY"
```
![](https://hackmd.io/_uploads/B1gg9khd22.png)

### 2-3 Deploy Kepler
```shell=
kubectl apply -f _output/generated-manifest/deployment.yaml
```
![](https://hackmd.io/_uploads/SJ88Zh_23.png)

### 2-4 Port Forwarding by tmux
```shell=
# Open new session
tmux new -s keplerPortForwarding

# Port Forwarding in new session
kubectl port-forward -n kepler kepler-exporter-544ds 9102:9102 --address=10.0.10.202
```
```shell=
# Verify the Port Forwarding
sudo lsof -i -n -P | grep LISTEN

# Check the tmux session
tmux ls

# Attach the tmux session
tmux attach -t keplerPortForwarding
```
## 3. Trouble Shooting
### 3-1 Error in building manifests
![](https://hackmd.io/_uploads/H1SyG2d32.png)
:::success
**Solution:**
```shell=
sudo apt update && sudo apt install golang
```
:::
### 3-2 Error log about ebpf not started
![](https://hackmd.io/_uploads/BJTAGhuhn.png)
:::success
**Solution:**
The following log is root cause
```
I0814 09:07:29.190477       1 bcc_attacher.go:155] failed to attach perf module with options [-DMAP_SIZE=10240 -DNUM_CPUS=4 -DSET_GROUP_ID]: failed to attach the bpf program: <nil>, from default kernel source.
I0814 09:07:29.190569       1 bcc_attacher.go:170] failed to attach perf module with options [-DMAP_SIZE=10240 -DNUM_CPUS=4 -DSET_GROUP_ID]: failed to attach the bpf program: <nil>, not able to load eBPF modules
```

Change the Kepler image from `latest` to `latest-libbpf`
```shell=
kubectl edit -n kepler daemonset kepler-exporter
```
```yaml=
spec:
      containers:
      - args:
        - until [ -e /tmp/estimator.sock ]; do sleep 1; done && /usr/bin/kepler -v=1
        command:
        - /bin/sh
        - -c
        env:
        - name: NODE_IP
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: status.hostIP
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: spec.nodeName
        image: quay.io/sustainable_computing_io/kepler:latest-libbpf    #Revise
        imagePullPolicy: Always
```
```
I0814 13:59:55.671043       1 gpu.go:46] Failed to init nvml, err: could not init nvml: error opening libnvidia-ml.so.1: libnvidia-ml.so.1: cannot open shared object file: No such file or directory
I0814 13:59:55.682049       1 exporter.go:156] Kepler running on version: 301f96b
I0814 13:59:55.682068       1 config.go:263] using gCgroup ID in the BPF program: true
I0814 13:59:55.682100       1 config.go:265] kernel version: 5.15
I0814 13:59:55.682128       1 exporter.go:181] EnabledBPFBatchDelete: true
I0814 13:59:55.682143       1 rapl_msr_util.go:129] failed to open path /dev/cpu/0/msr: no such file or directory
I0814 13:59:55.682177       1 power.go:71] Unable to obtain power, use estimate method
I0814 13:59:55.682185       1 redfish.go:169] failed to get redfish credential file path
I0814 13:59:55.682189       1 power.go:56] use acpi to obtain power
I0814 13:59:55.682331       1 acpi.go:67] Could not find any ACPI power meter path. Is it a VM?
I0814 13:59:55.688077       1 container_energy.go:109] Using the Ratio/AbsPower Power Model to estimate Container Platform Power
I0814 13:59:56.091302       1 container_energy.go:118] Using the EstimatorSidecar/DynComponentPower Power Model to estimate Container Component Power
I0814 13:59:56.091380       1 process_power.go:108] Using the Ratio/AbsPower Power Model to estimate Process Platform Power
I0814 13:59:56.091397       1 process_power.go:117] Using the Ratio/AbsPower Power Model to estimate Process Component Power
I0814 13:59:56.095246       1 node_platform_energy.go:52] Using the LinearRegressor/AbsModelWeight Power Model to estimate Node Platform Power
I0814 13:59:56.095578       1 node_component_energy.go:56] Using the LinearRegressor/AbsComponentModelWeight Power Model to estimate Node Component Power
I0814 13:59:56.095639       1 exporter.go:204] Initializing the GPU collector
I0814 14:00:02.101263       1 watcher.go:66] Using in cluster k8s config
I0814 14:00:02.203023       1 bpf_perf.go:123] LibbpfBuilt: true, BccBuilt: false
libbpf: loading /var/lib/kepler/bpfassets/amd64_kepler.bpf.o
libbpf: elf: section(3) tracepoint/sched/sched_switch, size 2352, link 0, flags 6, type=1
libbpf: sec 'tracepoint/sched/sched_switch': found program 'kepler_trace' at insn offset 0 (0 bytes), code size 294 insns (2352 bytes)
libbpf: elf: section(4) .reltracepoint/sched/sched_switch, size 352, link 26, flags 40, type=9
libbpf: elf: section(5) tracepoint/irq/softirq_entry, size 144, link 0, flags 6, type=1
libbpf: sec 'tracepoint/irq/softirq_entry': found program 'kepler_irq_trace' at insn offset 0 (0 bytes), code size 18 insns (144 bytes)
libbpf: elf: section(6) .reltracepoint/irq/softirq_entry, size 16, link 26, flags 40, type=9
libbpf: elf: section(7) .maps, size 352, link 0, flags 3, type=1
libbpf: elf: section(8) license, size 4, link 0, flags 3, type=1
libbpf: license of /var/lib/kepler/bpfassets/amd64_kepler.bpf.o is GPL
libbpf: elf: section(17) .BTF, size 5820, link 0, flags 0, type=1
libbpf: elf: section(19) .BTF.ext, size 2056, link 0, flags 0, type=1
libbpf: elf: section(26) .symtab, size 984, link 1, flags 0, type=2
libbpf: looking for externs among 41 symbols...
libbpf: collected 0 externs total
libbpf: map 'processes': at sec_idx 7, offset 0.
libbpf: map 'processes': found type = 1.
libbpf: map 'processes': found key [6], sz = 4.
libbpf: map 'processes': found value [10], sz = 88.
libbpf: map 'processes': found max_entries = 10240.
libbpf: map 'pid_time': at sec_idx 7, offset 32.
libbpf: map 'pid_time': found type = 1.
libbpf: map 'pid_time': found key [6], sz = 4.
libbpf: map 'pid_time': found value [12], sz = 8.
libbpf: map 'pid_time': found max_entries = 10240.
libbpf: map 'cpu_cycles_hc_reader': at sec_idx 7, offset 64.
libbpf: map 'cpu_cycles_hc_reader': found type = 4.
libbpf: map 'cpu_cycles_hc_reader': found key [2], sz = 4.
libbpf: map 'cpu_cycles_hc_reader': found value [6], sz = 4.
libbpf: map 'cpu_cycles_hc_reader': found max_entries = 128.
libbpf: map 'cpu_cycles': at sec_idx 7, offset 96.
libbpf: map 'cpu_cycles': found type = 2.
libbpf: map 'cpu_cycles': found key [6], sz = 4.
libbpf: map 'cpu_cycles': found value [12], sz = 8.
libbpf: map 'cpu_cycles': found max_entries = 128.
libbpf: map 'cpu_ref_cycles_hc_reader': at sec_idx 7, offset 128.
libbpf: map 'cpu_ref_cycles_hc_reader': found type = 4.
libbpf: map 'cpu_ref_cycles_hc_reader': found key [2], sz = 4.
libbpf: map 'cpu_ref_cycles_hc_reader': found value [6], sz = 4.
libbpf: map 'cpu_ref_cycles_hc_reader': found max_entries = 128.
libbpf: map 'cpu_ref_cycles': at sec_idx 7, offset 160.
libbpf: map 'cpu_ref_cycles': found type = 2.
libbpf: map 'cpu_ref_cycles': found key [6], sz = 4.
libbpf: map 'cpu_ref_cycles': found value [12], sz = 8.
libbpf: map 'cpu_ref_cycles': found max_entries = 128.
libbpf: map 'cpu_instr_hc_reader': at sec_idx 7, offset 192.
libbpf: map 'cpu_instr_hc_reader': found type = 4.
libbpf: map 'cpu_instr_hc_reader': found key [2], sz = 4.
libbpf: map 'cpu_instr_hc_reader': found value [6], sz = 4.
libbpf: map 'cpu_instr_hc_reader': found max_entries = 128.
libbpf: map 'cpu_instr': at sec_idx 7, offset 224.
libbpf: map 'cpu_instr': found type = 2.
libbpf: map 'cpu_instr': found key [6], sz = 4.
libbpf: map 'cpu_instr': found value [12], sz = 8.
libbpf: map 'cpu_instr': found max_entries = 128.
libbpf: map 'cache_miss_hc_reader': at sec_idx 7, offset 256.
libbpf: map 'cache_miss_hc_reader': found type = 4.
libbpf: map 'cache_miss_hc_reader': found key [2], sz = 4.
libbpf: map 'cache_miss_hc_reader': found value [6], sz = 4.
libbpf: map 'cache_miss_hc_reader': found max_entries = 128.
libbpf: map 'cache_miss': at sec_idx 7, offset 288.
libbpf: map 'cache_miss': found type = 2.
libbpf: map 'cache_miss': found key [6], sz = 4.
libbpf: map 'cache_miss': found value [12], sz = 8.
libbpf: map 'cache_miss': found max_entries = 128.
libbpf: map 'cpu_freq_array': at sec_idx 7, offset 320.
libbpf: map 'cpu_freq_array': found type = 2.
libbpf: map 'cpu_freq_array': found key [6], sz = 4.
libbpf: map 'cpu_freq_array': found value [6], sz = 4.
libbpf: map 'cpu_freq_array': found max_entries = 128.
libbpf: sec '.reltracepoint/sched/sched_switch': collecting relocation for section(3) 'tracepoint/sched/sched_switch'
libbpf: sec '.reltracepoint/sched/sched_switch': relo #0: insn #17 against 'cpu_cycles_hc_reader'
libbpf: prog 'kepler_trace': found map 2 (cpu_cycles_hc_reader, sec 7, off 64) for insn #17
libbpf: sec '.reltracepoint/sched/sched_switch': relo #1: insn #36 against 'cpu_cycles'
libbpf: prog 'kepler_trace': found map 3 (cpu_cycles, sec 7, off 96) for insn #36
libbpf: sec '.reltracepoint/sched/sched_switch': relo #2: insn #50 against 'cpu_cycles'
libbpf: prog 'kepler_trace': found map 3 (cpu_cycles, sec 7, off 96) for insn #50
libbpf: sec '.reltracepoint/sched/sched_switch': relo #3: insn #55 against 'cpu_ref_cycles_hc_reader'
libbpf: prog 'kepler_trace': found map 4 (cpu_ref_cycles_hc_reader, sec 7, off 128) for insn #55
libbpf: sec '.reltracepoint/sched/sched_switch': relo #4: insn #68 against 'cpu_ref_cycles'
libbpf: prog 'kepler_trace': found map 5 (cpu_ref_cycles, sec 7, off 160) for insn #68
libbpf: sec '.reltracepoint/sched/sched_switch': relo #5: insn #82 against 'cpu_ref_cycles'
libbpf: prog 'kepler_trace': found map 5 (cpu_ref_cycles, sec 7, off 160) for insn #82
libbpf: sec '.reltracepoint/sched/sched_switch': relo #6: insn #87 against 'cpu_instr_hc_reader'
libbpf: prog 'kepler_trace': found map 6 (cpu_instr_hc_reader, sec 7, off 192) for insn #87
libbpf: sec '.reltracepoint/sched/sched_switch': relo #7: insn #104 against 'cpu_instr'
libbpf: prog 'kepler_trace': found map 7 (cpu_instr, sec 7, off 224) for insn #104
libbpf: sec '.reltracepoint/sched/sched_switch': relo #8: insn #117 against 'cpu_instr'
libbpf: prog 'kepler_trace': found map 7 (cpu_instr, sec 7, off 224) for insn #117
libbpf: sec '.reltracepoint/sched/sched_switch': relo #9: insn #122 against 'cache_miss_hc_reader'
libbpf: prog 'kepler_trace': found map 8 (cache_miss_hc_reader, sec 7, off 256) for insn #122
libbpf: sec '.reltracepoint/sched/sched_switch': relo #10: insn #134 against 'cache_miss'
libbpf: prog 'kepler_trace': found map 9 (cache_miss, sec 7, off 288) for insn #134
libbpf: sec '.reltracepoint/sched/sched_switch': relo #11: insn #148 against 'cache_miss'
libbpf: prog 'kepler_trace': found map 9 (cache_miss, sec 7, off 288) for insn #148
libbpf: sec '.reltracepoint/sched/sched_switch': relo #12: insn #156 against 'cpu_freq_array'
libbpf: prog 'kepler_trace': found map 10 (cpu_freq_array, sec 7, off 320) for insn #156
libbpf: sec '.reltracepoint/sched/sched_switch': relo #13: insn #170 against 'cpu_freq_array'
libbpf: prog 'kepler_trace': found map 10 (cpu_freq_array, sec 7, off 320) for insn #170
libbpf: sec '.reltracepoint/sched/sched_switch': relo #14: insn #182 against 'cpu_freq_array'
libbpf: prog 'kepler_trace': found map 10 (cpu_freq_array, sec 7, off 320) for insn #182
libbpf: sec '.reltracepoint/sched/sched_switch': relo #15: insn #206 against 'cpu_freq_array'
libbpf: prog 'kepler_trace': found map 10 (cpu_freq_array, sec 7, off 320) for insn #206
libbpf: sec '.reltracepoint/sched/sched_switch': relo #16: insn #215 against 'pid_time'
libbpf: prog 'kepler_trace': found map 1 (pid_time, sec 7, off 32) for insn #215
libbpf: sec '.reltracepoint/sched/sched_switch': relo #17: insn #223 against 'pid_time'
libbpf: prog 'kepler_trace': found map 1 (pid_time, sec 7, off 32) for insn #223
libbpf: sec '.reltracepoint/sched/sched_switch': relo #18: insn #235 against 'pid_time'
libbpf: prog 'kepler_trace': found map 1 (pid_time, sec 7, off 32) for insn #235
libbpf: sec '.reltracepoint/sched/sched_switch': relo #19: insn #241 against 'processes'
libbpf: prog 'kepler_trace': found map 0 (processes, sec 7, off 0) for insn #241
libbpf: sec '.reltracepoint/sched/sched_switch': relo #20: insn #263 against 'processes'
libbpf: prog 'kepler_trace': found map 0 (processes, sec 7, off 0) for insn #263
libbpf: sec '.reltracepoint/sched/sched_switch': relo #21: insn #288 against 'processes'
libbpf: prog 'kepler_trace': found map 0 (processes, sec 7, off 0) for insn #288
libbpf: sec '.reltracepoint/irq/softirq_entry': collecting relocation for section(5) 'tracepoint/irq/softirq_entry'
libbpf: sec '.reltracepoint/irq/softirq_entry': relo #0: insn #5 against 'processes'
libbpf: prog 'kepler_irq_trace': found map 0 (processes, sec 7, off 0) for insn #5
libbpf: map 'processes': created successfully, fd=10
libbpf: map 'pid_time': created successfully, fd=11
libbpf: map 'cpu_cycles_hc_reader': created successfully, fd=12
libbpf: map 'cpu_cycles': created successfully, fd=13
libbpf: map 'cpu_ref_cycles_hc_reader': created successfully, fd=14
libbpf: map 'cpu_ref_cycles': created successfully, fd=15
libbpf: map 'cpu_instr_hc_reader': created successfully, fd=16
libbpf: map 'cpu_instr': created successfully, fd=17
libbpf: map 'cache_miss_hc_reader': created successfully, fd=18
libbpf: map 'cache_miss': created successfully, fd=19
libbpf: map 'cpu_freq_array': created successfully, fd=20
I0814 14:00:02.207110       1 libbpf_attacher.go:153] Successfully load eBPF module from libbpf object
I0814 14:00:02.219268       1 exporter.go:257] Started Kepler in 6.537229901s
```
:::

### 3.3 Error about pulling Kepler Model Server image
![](https://hackmd.io/_uploads/B1GGON963.png)
:::success
**Solution**
Kepler have released the v0.6 image.
Change the estimator image.
```shell=
kubectl edit -n kepler daemonset kepler-exporter
```
```yaml=
- args:
        - -u
        - src/estimate/estimator.py
        command:
        - python3.8
        image: quay.io/sustainable_computing_io/kepler_model_server:v0.6
        imagePullPolicy: IfNotPresent
        name: estimator
        resources: {}
        terminationMessagePath: /dev/termination-log
        terminationMessagePolicy: File
```
```
I0828 11:44:43.463430       1 gpu.go:46] Failed to init nvml, err: could not init nvml: error opening libnvidia-ml.so.1: libnvidia-ml.so.1: cannot open shared object file: No such file or directory
I0828 11:44:43.468290       1 qat.go:35] Failed to init qat-telemtry err: could not get qat status exit status 127
I0828 11:44:43.477644       1 exporter.go:158] Kepler running on version: fad28b7
I0828 11:44:43.477694       1 config.go:270] using gCgroup ID in the BPF program: true
I0828 11:44:43.477748       1 config.go:272] kernel version: 5.15
I0828 11:44:43.477810       1 exporter.go:170] LibbpfBuilt: true, BccBuilt: false
I0828 11:44:43.477846       1 exporter.go:189] EnabledBPFBatchDelete: true
I0828 11:44:43.477890       1 rapl_msr_util.go:129] failed to open path /dev/cpu/0/msr: no such file or directory
I0828 11:44:43.477995       1 power.go:71] Unable to obtain power, use estimate method
I0828 11:44:43.478043       1 redfish.go:173] failed to initialize node credential: no supported node credential implementation
I0828 11:44:43.478050       1 power.go:56] use acpi to obtain power
I0828 11:44:43.478243       1 acpi.go:67] Could not find any ACPI power meter path. Is it a VM?
I0828 11:44:43.493568       1 container_energy.go:109] Using the Ratio/DynPower Power Model to estimate Container Platform Power
I0828 11:44:43.493589       1 container_energy.go:118] Using the Ratio/DynPower Power Model to estimate Container Component Power
I0828 11:44:43.493617       1 process_power.go:108] Using the Ratio/DynPower Power Model to estimate Process Platform Power
I0828 11:44:43.493627       1 process_power.go:117] Using the Ratio/DynPower Power Model to estimate Process Component Power
I0828 11:44:43.493803       1 node_platform_energy.go:53] Using the LinearRegressor/AbsPower Power Model to estimate Node Platform Power
I0828 11:44:44.709229       1 node_component_energy.go:54] Using the EstimatorSidecar/AbsPower Power Model to estimate Node Component Power
I0828 11:44:44.709405       1 exporter.go:212] Initializing the GPU collector
I0828 11:44:50.714948       1 watcher.go:66] Using in cluster k8s config
libbpf: loading /var/lib/kepler/bpfassets/amd64_kepler.bpf.o
libbpf: elf: section(3) tracepoint/sched/sched_switch, size 2344, link 0, flags 6, type=1
libbpf: sec 'tracepoint/sched/sched_switch': found program 'kepler_trace' at insn offset 0 (0 bytes), code size 293 insns (2344 bytes)
libbpf: elf: section(4) .reltracepoint/sched/sched_switch, size 352, link 29, flags 40, type=9
libbpf: elf: section(5) tracepoint/irq/softirq_entry, size 144, link 0, flags 6, type=1
libbpf: sec 'tracepoint/irq/softirq_entry': found program 'kepler_irq_trace' at insn offset 0 (0 bytes), code size 18 insns (144 bytes)
libbpf: elf: section(6) .reltracepoint/irq/softirq_entry, size 16, link 29, flags 40, type=9
libbpf: elf: section(7) .maps, size 352, link 0, flags 3, type=1
libbpf: elf: section(8) license, size 4, link 0, flags 3, type=1
libbpf: license of /var/lib/kepler/bpfassets/amd64_kepler.bpf.o is GPL
libbpf: elf: section(19) .BTF, size 5759, link 0, flags 0, type=1
libbpf: elf: section(21) .BTF.ext, size 2120, link 0, flags 0, type=1
libbpf: elf: section(29) .symtab, size 1056, link 1, flags 0, type=2
libbpf: looking for externs among 44 symbols...
libbpf: collected 0 externs total
libbpf: map 'processes': at sec_idx 7, offset 0.
libbpf: map 'processes': found type = 1.
libbpf: map 'processes': found key [6], sz = 4.
libbpf: map 'processes': found value [10], sz = 88.
libbpf: map 'processes': found max_entries = 32768.
libbpf: map 'pid_time': at sec_idx 7, offset 32.
libbpf: map 'pid_time': found type = 1.
libbpf: map 'pid_time': found key [6], sz = 4.
libbpf: map 'pid_time': found value [12], sz = 8.
libbpf: map 'pid_time': found max_entries = 32768.
libbpf: map 'cpu_cycles_hc_reader': at sec_idx 7, offset 64.
libbpf: map 'cpu_cycles_hc_reader': found type = 4.
libbpf: map 'cpu_cycles_hc_reader': found key [2], sz = 4.
libbpf: map 'cpu_cycles_hc_reader': found value [6], sz = 4.
libbpf: map 'cpu_cycles_hc_reader': found max_entries = 128.
libbpf: map 'cpu_cycles': at sec_idx 7, offset 96.
libbpf: map 'cpu_cycles': found type = 2.
libbpf: map 'cpu_cycles': found key [6], sz = 4.
libbpf: map 'cpu_cycles': found value [12], sz = 8.
libbpf: map 'cpu_cycles': found max_entries = 128.
libbpf: map 'cpu_ref_cycles_hc_reader': at sec_idx 7, offset 128.
libbpf: map 'cpu_ref_cycles_hc_reader': found type = 4.
libbpf: map 'cpu_ref_cycles_hc_reader': found key [2], sz = 4.
libbpf: map 'cpu_ref_cycles_hc_reader': found value [6], sz = 4.
libbpf: map 'cpu_ref_cycles_hc_reader': found max_entries = 128.
libbpf: map 'cpu_ref_cycles': at sec_idx 7, offset 160.
libbpf: map 'cpu_ref_cycles': found type = 2.
libbpf: map 'cpu_ref_cycles': found key [6], sz = 4.
libbpf: map 'cpu_ref_cycles': found value [12], sz = 8.
libbpf: map 'cpu_ref_cycles': found max_entries = 128.
libbpf: map 'cpu_instr_hc_reader': at sec_idx 7, offset 192.
libbpf: map 'cpu_instr_hc_reader': found type = 4.
libbpf: map 'cpu_instr_hc_reader': found key [2], sz = 4.
libbpf: map 'cpu_instr_hc_reader': found value [6], sz = 4.
libbpf: map 'cpu_instr_hc_reader': found max_entries = 128.
libbpf: map 'cpu_instr': at sec_idx 7, offset 224.
libbpf: map 'cpu_instr': found type = 2.
libbpf: map 'cpu_instr': found key [6], sz = 4.
libbpf: map 'cpu_instr': found value [12], sz = 8.
libbpf: map 'cpu_instr': found max_entries = 128.
libbpf: map 'cache_miss_hc_reader': at sec_idx 7, offset 256.
libbpf: map 'cache_miss_hc_reader': found type = 4.
libbpf: map 'cache_miss_hc_reader': found key [2], sz = 4.
libbpf: map 'cache_miss_hc_reader': found value [6], sz = 4.
libbpf: map 'cache_miss_hc_reader': found max_entries = 128.
libbpf: map 'cache_miss': at sec_idx 7, offset 288.
libbpf: map 'cache_miss': found type = 2.
libbpf: map 'cache_miss': found key [6], sz = 4.
libbpf: map 'cache_miss': found value [12], sz = 8.
libbpf: map 'cache_miss': found max_entries = 128.
libbpf: map 'cpu_freq_array': at sec_idx 7, offset 320.
libbpf: map 'cpu_freq_array': found type = 2.
libbpf: map 'cpu_freq_array': found key [6], sz = 4.
libbpf: map 'cpu_freq_array': found value [6], sz = 4.
libbpf: map 'cpu_freq_array': found max_entries = 128.
libbpf: sec '.reltracepoint/sched/sched_switch': collecting relocation for section(3) 'tracepoint/sched/sched_switch'
libbpf: sec '.reltracepoint/sched/sched_switch': relo #0: insn #17 against 'cpu_cycles_hc_reader'
libbpf: prog 'kepler_trace': found map 2 (cpu_cycles_hc_reader, sec 7, off 64) for insn #17
libbpf: sec '.reltracepoint/sched/sched_switch': relo #1: insn #36 against 'cpu_cycles'
libbpf: prog 'kepler_trace': found map 3 (cpu_cycles, sec 7, off 96) for insn #36
libbpf: sec '.reltracepoint/sched/sched_switch': relo #2: insn #50 against 'cpu_cycles'
libbpf: prog 'kepler_trace': found map 3 (cpu_cycles, sec 7, off 96) for insn #50
libbpf: sec '.reltracepoint/sched/sched_switch': relo #3: insn #55 against 'cpu_ref_cycles_hc_reader'
libbpf: prog 'kepler_trace': found map 4 (cpu_ref_cycles_hc_reader, sec 7, off 128) for insn #55
libbpf: sec '.reltracepoint/sched/sched_switch': relo #4: insn #68 against 'cpu_ref_cycles'
libbpf: prog 'kepler_trace': found map 5 (cpu_ref_cycles, sec 7, off 160) for insn #68
libbpf: sec '.reltracepoint/sched/sched_switch': relo #5: insn #82 against 'cpu_ref_cycles'
libbpf: prog 'kepler_trace': found map 5 (cpu_ref_cycles, sec 7, off 160) for insn #82
libbpf: sec '.reltracepoint/sched/sched_switch': relo #6: insn #87 against 'cpu_instr_hc_reader'
libbpf: prog 'kepler_trace': found map 6 (cpu_instr_hc_reader, sec 7, off 192) for insn #87
libbpf: sec '.reltracepoint/sched/sched_switch': relo #7: insn #104 against 'cpu_instr'
libbpf: prog 'kepler_trace': found map 7 (cpu_instr, sec 7, off 224) for insn #104
libbpf: sec '.reltracepoint/sched/sched_switch': relo #8: insn #117 against 'cpu_instr'
libbpf: prog 'kepler_trace': found map 7 (cpu_instr, sec 7, off 224) for insn #117
libbpf: sec '.reltracepoint/sched/sched_switch': relo #9: insn #122 against 'cache_miss_hc_reader'
libbpf: prog 'kepler_trace': found map 8 (cache_miss_hc_reader, sec 7, off 256) for insn #122
libbpf: sec '.reltracepoint/sched/sched_switch': relo #10: insn #134 against 'cache_miss'
libbpf: prog 'kepler_trace': found map 9 (cache_miss, sec 7, off 288) for insn #134
libbpf: sec '.reltracepoint/sched/sched_switch': relo #11: insn #148 against 'cache_miss'
libbpf: prog 'kepler_trace': found map 9 (cache_miss, sec 7, off 288) for insn #148
libbpf: sec '.reltracepoint/sched/sched_switch': relo #12: insn #156 against 'cpu_freq_array'
libbpf: prog 'kepler_trace': found map 10 (cpu_freq_array, sec 7, off 320) for insn #156
libbpf: sec '.reltracepoint/sched/sched_switch': relo #13: insn #170 against 'cpu_freq_array'
libbpf: prog 'kepler_trace': found map 10 (cpu_freq_array, sec 7, off 320) for insn #170
libbpf: sec '.reltracepoint/sched/sched_switch': relo #14: insn #182 against 'cpu_freq_array'
libbpf: prog 'kepler_trace': found map 10 (cpu_freq_array, sec 7, off 320) for insn #182
libbpf: sec '.reltracepoint/sched/sched_switch': relo #15: insn #206 against 'cpu_freq_array'
libbpf: prog 'kepler_trace': found map 10 (cpu_freq_array, sec 7, off 320) for insn #206
libbpf: sec '.reltracepoint/sched/sched_switch': relo #16: insn #215 against 'pid_time'
libbpf: prog 'kepler_trace': found map 1 (pid_time, sec 7, off 32) for insn #215
libbpf: sec '.reltracepoint/sched/sched_switch': relo #17: insn #223 against 'pid_time'
libbpf: prog 'kepler_trace': found map 1 (pid_time, sec 7, off 32) for insn #223
libbpf: sec '.reltracepoint/sched/sched_switch': relo #18: insn #235 against 'pid_time'
libbpf: prog 'kepler_trace': found map 1 (pid_time, sec 7, off 32) for insn #235
libbpf: sec '.reltracepoint/sched/sched_switch': relo #19: insn #241 against 'processes'
libbpf: prog 'kepler_trace': found map 0 (processes, sec 7, off 0) for insn #241
libbpf: sec '.reltracepoint/sched/sched_switch': relo #20: insn #261 against 'processes'
libbpf: prog 'kepler_trace': found map 0 (processes, sec 7, off 0) for insn #261
libbpf: sec '.reltracepoint/sched/sched_switch': relo #21: insn #287 against 'processes'
libbpf: prog 'kepler_trace': found map 0 (processes, sec 7, off 0) for insn #287
libbpf: sec '.reltracepoint/irq/softirq_entry': collecting relocation for section(5) 'tracepoint/irq/softirq_entry'
libbpf: sec '.reltracepoint/irq/softirq_entry': relo #0: insn #5 against 'processes'
libbpf: prog 'kepler_irq_trace': found map 0 (processes, sec 7, off 0) for insn #5
libbpf: map 'processes': created successfully, fd=10
libbpf: map 'pid_time': created successfully, fd=11
libbpf: map 'cpu_cycles_hc_reader': created successfully, fd=12
libbpf: map 'cpu_cycles': created successfully, fd=13
libbpf: map 'cpu_ref_cycles_hc_reader': created successfully, fd=14
libbpf: map 'cpu_ref_cycles': created successfully, fd=15
libbpf: map 'cpu_instr_hc_reader': created successfully, fd=16
libbpf: map 'cpu_instr': created successfully, fd=17
libbpf: map 'cache_miss_hc_reader': created successfully, fd=18
libbpf: map 'cache_miss': created successfully, fd=19
libbpf: map 'cpu_freq_array': created successfully, fd=20
I0828 11:44:50.823749       1 libbpf_attacher.go:143] failed to get perf event cpu_instructions_hc_reader: failed to find BPF map cpu_instructions_hc_reader: no such file or directory
I0828 11:44:50.824146       1 libbpf_attacher.go:157] Successfully load eBPF module from libbpf object
I0828 11:44:50.857140       1 exporter.go:276] Started Kepler in 7.379527116s

```
:::

### 3.4 cannot extract:metrics
![](https://hackmd.io/_uploads/HySCTWGA2.png)
:::success
**Solution**
This is because you are running on a VM, which does not have hardware counter metrics and does not seems to have GPU metrics.
:::
# Appendix
### Integrate with Prometheus Server of Near-RT RIC Platform

**Let Prometheus Server of Near-RT RIC Platform can captrue the Kepler metrics.**
```shell=
cd ric-dep/helm/infrastructure/subcharts/prometheus
vim values.yaml
```

**Add the job in the Prometheus Server. And re-install it.**
```yaml=
prometheus.yml:
    rule_files:
      - /etc/config/recording_rules.yml
      - /etc/config/alerting_rules.yml
    ## Below two files are DEPRECATED will be removed from this default values file
      - /etc/config/rules
      - /etc/config/alerts

    scrape_configs:
      - job_name: prometheus
        static_configs:
          - targets:
            - localhost:9090
        
        
      # A scrape configuration for running Prometheus on a Kubernetes cluster.
      # This uses separate scrape configs for cluster components (i.e. API server, node)
      # and services to allow each to use different authentication configs.
      #
      # Kubernetes labels will be added as Prometheus labels on metrics via the
      # `labelmap` relabeling action.

      # Scrape config for API servers.
      #
      # Kubernetes exposes API servers as endpoints to the default/kubernetes
      # service so this uses `endpoints` role and uses relabelling to only keep
      # the endpoints associated with the default/kubernetes service using the
      # default named port `https`. This works for single API server deployments as
      # well as HA API server deployments.
      - job_name: 'kepler-exporter'

        static_configs:
          - targets: ['192.168.8.220:9102']

        scrape_interval: 5s
        scrape_timeout: 5s
```

**Revise the svc config ClusterIP -> NodePort**
```shell=
kubectl edit svc -n ricplt r4-infrastructure-prometheus-server
```
```yaml=
spec:
  clusterIP: 10.98.209.86
  externalTrafficPolicy: Cluster
  ports:
  - name: http
    nodePort: 32000    # add nodePort
    port: 80
    protocol: TCP
    targetPort: 9090
  selector:
    app: prometheus
    component: server
    release: r4-infrastructure
  sessionAffinity: None
  type: NodePort    # revise ClusterIP -> NodePort
status:
  loadBalancer: {}

```