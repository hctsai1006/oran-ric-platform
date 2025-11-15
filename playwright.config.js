/**
 * Playwright Test Configuration for O-RAN RIC Platform
 *
 * This configuration is used for E2E testing of Grafana dashboards
 * and other web-based components of the RIC platform.
 *
 * Author: Tsai Hsiu-Chi (thc1006)
 */

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',

  // Test execution settings
  fullyParallel: false, // Run tests sequentially to avoid conflicts
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1, // Single worker for dashboard tests

  // Timeout settings
  timeout: 60000, // 60 seconds per test
  expect: {
    timeout: 10000 // 10 seconds for assertions
  },

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'test-results/html-report' }],
    ['json', { outputFile: 'test-results/test-results.json' }],
    ['list']
  ],

  // Output directory
  outputDir: 'test-results/artifacts',

  // Shared settings for all tests
  use: {
    // Base URL for navigation
    baseURL: process.env.GRAFANA_URL || 'http://localhost:3000',

    // Browser settings
    headless: true, // Always run in headless mode
    viewport: { width: 1920, height: 1080 },

    // Capture settings
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',

    // Action settings
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  // Test projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Override viewport for consistent screenshots
        viewport: { width: 1920, height: 1080 },
        // Launch options for headless mode without X server
        launchOptions: {
          args: [
            '--headless=new',  // Use new headless mode (doesn't require X server)
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
          ]
        }
      },
    },

    // Uncomment to test on other browsers
    /*
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    */
  ],

  // Web server configuration (if needed)
  // webServer: {
  //   command: 'npm run start',
  //   port: 3000,
  //   reuseExistingServer: !process.env.CI,
  // },
});
