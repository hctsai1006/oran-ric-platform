---
name: deploy-xapp
description: Deploy and verify xApp to RIC platform
allowed-tools: 
  - kubectl:*
  - helm:*
  - dms_cli:*
  - docker:*
parameters:
  - name: xapp-name
    type: string
    required: true
    description: Name of the xApp to deploy
  - name: version
    type: string
    required: false
    default: latest
    description: Version tag for the xApp
---

# Deploy xApp: $xapp-name

Execute the following deployment sequence for the specified xApp:

## Pre-deployment Checks
1. Verify xApp directory exists: `xapps/$xapp-name/`
2. Check if xApp descriptor exists: `xapps/$xapp-name/config/xapp-descriptor.json`
3. Validate JSON schema: `jq . xapps/$xapp-name/config/xapp-descriptor.json`

## Build and Push Image
```bash
cd xapps/$xapp-name
docker build -t localhost:5000/$xapp-name:$version .
docker push localhost:5000/$xapp-name:$version
```

## Onboard xApp
```bash
dms_cli onboard \
  --config_file_path=./config/xapp-descriptor.json \
  --schema_file_path=./config/schema.json
```

## Verify Onboarding
```bash
curl http://$(kubectl get svc -n ricplt appmgr-http -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8080/onboard/api/v1/charts
```

## Install xApp
```bash
dms_cli install \
  --xapp_chart_name=$xapp-name \
  --version=$version \
  --namespace=ricxapp
```

## Verification Steps
1. Check deployment status:
   ```bash
   kubectl get pods -n ricxapp -l app=$xapp-name
   kubectl wait --for=condition=ready pod -l app=$xapp-name -n ricxapp --timeout=300s
   ```

2. Verify RMR connectivity:
   ```bash
   kubectl logs -n ricxapp -l app=$xapp-name | grep "RMR is ready"
   ```

3. Check health endpoint:
   ```bash
   POD_IP=$(kubectl get pod -n ricxapp -l app=$xapp-name -o jsonpath='{.items[0].status.podIP}')
   curl http://$POD_IP:8080/ric/v1/health/alive
   ```

4. Monitor E2 subscription (if applicable):
   ```bash
   kubectl logs -n ricxapp -l app=$xapp-name | grep "Subscription successful"
   ```

## Troubleshooting
If deployment fails:
- Check logs: `kubectl logs -n ricxapp -l app=$xapp-name --tail=100`
- Describe pod: `kubectl describe pod -n ricxapp -l app=$xapp-name`
- Check events: `kubectl get events -n ricxapp --sort-by='.lastTimestamp'`
- Verify RMR route table: `kubectl exec -it -n ricxapp <pod-name> -- cat /opt/route/rmr.rt`

Report deployment status with specific error messages if any step fails.
