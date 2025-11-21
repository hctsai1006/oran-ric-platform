const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('=== Testing RIC Dashboard ===\n');

  try {
    // Test 1: Load main page
    console.log('1. Testing main page load...');
    await page.goto('http://localhost:38888', { waitUntil: 'networkidle', timeout: 30000 });
    const title = await page.title();
    console.log(`   ✓ Page title: ${title}`);

    // Test 2: Check if Angular app loaded
    console.log('\n2. Testing Angular app...');
    const appRoot = await page.locator('app-root').count();
    console.log(`   ${appRoot > 0 ? '✓' : '✗'} app-root element: ${appRoot > 0 ? 'Found' : 'Not found'}`);

    // Test 3: Wait for Angular to bootstrap
    await page.waitForTimeout(3000);

    // Test 4: Check for navigation
    console.log('\n3. Testing navigation...');
    const navExists = await page.locator('mat-toolbar').count();
    console.log(`   ${navExists > 0 ? '✓' : '✗'} Navigation toolbar: ${navExists > 0 ? 'Found' : 'Not found'}`);

    // Test 5: Check for MBWCL logo
    const logoExists = await page.getByText('MBWCL').count();
    console.log(`   ${logoExists > 0 ? '✓' : '✗'} MBWCL Logo: ${logoExists > 0 ? 'Found' : 'Not found'}`);

    // Test 6: Test API endpoints
    console.log('\n4. Testing API endpoints...');

    const healthResponse = await page.request.get('http://localhost:38888/health');
    const healthStatus = healthResponse.ok();
    const healthData = await healthResponse.json();
    console.log(`   ${healthStatus ? '✓' : '✗'} /health: ${healthStatus ? 'OK' : 'FAILED'}`);
    if (healthStatus) {
      console.log(`      Status: ${healthData.status}, Service: ${healthData.service}`);
    }

    const xappsResponse = await page.request.get('http://localhost:38888/api/xapps');
    const xappsStatus = xappsResponse.ok();
    console.log(`   ${xappsStatus ? '✓' : '✗'} /api/xapps: ${xappsStatus ? 'OK' : 'FAILED'}`);
    if (xappsStatus) {
      const xappsData = await xappsResponse.json();
      console.log(`      Found ${xappsData.length} xApps`);
      if (xappsData.length > 0) {
        console.log(`      First xApp: ${xappsData[0].name} (${xappsData[0].status})`);
      }
    } else {
      const errorText = await xappsResponse.text();
      console.log(`      Error: ${errorText.substring(0, 200)}`);
    }

    // Test 7: Check console errors
    console.log('\n5. Checking browser console...');
    const logs = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        logs.push(msg.text());
      }
    });

    await page.waitForTimeout(2000);

    if (logs.length === 0) {
      console.log('   ✓ No console errors');
    } else {
      console.log(`   ✗ Found ${logs.length} console errors:`);
      logs.forEach((log, i) => {
        console.log(`      ${i + 1}. ${log.substring(0, 100)}`);
      });
    }

    // Test 8: Take screenshot
    console.log('\n6. Taking screenshot...');
    await page.screenshot({
      path: '/home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/ric-dashboard/dashboard-screenshot.png',
      fullPage: true
    });
    console.log('   ✓ Screenshot saved: dashboard-screenshot.png');

    // Test 9: Get page content summary
    console.log('\n7. Page content summary...');
    const bodyText = await page.locator('body').textContent();
    console.log(`   Total text length: ${bodyText.length} characters`);

    console.log('\n=== Test Summary ===');
    console.log(`Angular app loaded: ${appRoot > 0 ? 'YES' : 'NO'}`);
    console.log(`Navigation present: ${navExists > 0 ? 'YES' : 'NO'}`);
    console.log(`MBWCL branding: ${logoExists > 0 ? 'YES' : 'NO'}`);
    console.log(`Health endpoint: ${healthStatus ? 'WORKING' : 'FAILED'}`);
    console.log(`xApps API: ${xappsStatus ? 'WORKING' : 'FAILED'}`);
    console.log(`Console errors: ${logs.length}`);

  } catch (error) {
    console.error('\n✗ Test failed with error:');
    console.error(error.message);
    console.error(error.stack);
  } finally {
    await browser.close();
  }
})();
