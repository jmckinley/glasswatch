/**
 * Discovery API Service
 * 
 * Client for asset discovery endpoints.
 */
import { apiClient } from './apiClient';

export interface Scanner {
  name: string;
  type: string;
  available: boolean;
  description: string;
  requires?: string[];
  error?: string;
}

export interface ScannerListResponse {
  scanners: Scanner[];
  total: number;
  available: number;
}

export interface TriggerScanRequest {
  scanners: string[];
  parallel?: boolean;
  update_existing?: boolean;
  aws_config?: Record<string, any>;
  azure_config?: Record<string, any>;
  gcp_config?: Record<string, any>;
  trivy_config?: Record<string, any>;
  kubescape_config?: Record<string, any>;
  servicenow_config?: Record<string, any>;
  nmap_config?: Record<string, any>;
  cloudquery_config?: Record<string, any>;
  jira_assets_config?: Record<string, any>;
  device42_config?: Record<string, any>;
}

export interface TriggerScanResponse {
  status: string;
  tenant_id: string;
  scanners: string[];
  message: string;
}

export interface DiscoveryStatus {
  status: string;
  started_at?: string;
  completed_at?: string;
  summary?: {
    status: string;
    duration_seconds: number;
    scanners_executed: number;
    assets_discovered: number;
    assets_after_deduplication: number;
    assets_created: number;
    assets_updated: number;
    total_errors: number;
    scanner_results: Array<{
      scanner: string;
      assets: number;
      duration: number;
      errors: number;
    }>;
  };
}

export interface AutoSyncConfig {
  enabled: boolean;
  scanners: string[];
  schedule: {
    type: 'interval' | 'cron';
    interval_hours?: number;
    cron_expr?: string;
  };
  next_run?: string;
}

export interface ConfigureAutoSyncResponse {
  status: string;
  enabled: boolean;
  scanners: string[];
  schedule: {
    type: string;
    interval_hours?: number;
    cron_expr?: string;
  };
  next_run?: string;
  message: string;
}

export const discoveryApi = {
  /**
   * List available scanners and their status
   */
  async listScanners(): Promise<ScannerListResponse> {
    const response = await apiClient.get('/discovery/scanners');
    return response.data;
  },

  /**
   * Trigger asset discovery scan
   */
  async triggerScan(config: TriggerScanRequest): Promise<TriggerScanResponse> {
    const response = await apiClient.post('/discovery/scan', config);
    return response.data;
  },

  /**
   * Get current discovery scan status
   */
  async getStatus(): Promise<DiscoveryStatus> {
    const response = await apiClient.get('/discovery/status');
    return response.data;
  },

  /**
   * Test scanner configuration
   */
  async testScanner(scanner: string, config: Record<string, any>): Promise<any> {
    const response = await apiClient.post('/discovery/test-scanner', {
      scanner,
      config
    });
    return response.data;
  },

  /**
   * Configure auto-sync
   */
  async configureAutoSync(config: AutoSyncConfig): Promise<ConfigureAutoSyncResponse> {
    const response = await apiClient.post('/discovery/auto-sync/configure', config);
    return response.data;
  },

  /**
   * Get auto-sync status
   */
  async getAutoSyncStatus(): Promise<AutoSyncConfig> {
    const response = await apiClient.get('/discovery/auto-sync/status');
    return response.data;
  },

  /**
   * List auto-sync jobs
   */
  async listAutoSyncJobs(): Promise<any> {
    const response = await apiClient.get('/discovery/auto-sync/jobs');
    return response.data;
  },

  /**
   * Get discovery history
   */
  async getHistory(limit: number = 10): Promise<any> {
    const response = await apiClient.get('/discovery/history', {
      params: { limit }
    });
    return response.data;
  }
};
