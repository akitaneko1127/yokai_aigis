import axios from 'axios';
import type { HazardResponse, YoukaiInfo, Location } from '../types';

const API_BASE_URL = '/api';

export const api = {
  // ハザード分析
  analyzeLocation: async (location: Location): Promise<HazardResponse> => {
    const response = await axios.post<HazardResponse>(
      `${API_BASE_URL}/hazard/analyze`,
      location
    );
    return response.data;
  },

  // 妖怪一覧
  getYoukaiList: async (): Promise<YoukaiInfo[]> => {
    const response = await axios.get<YoukaiInfo[]>(
      `${API_BASE_URL}/youkai/list`
    );
    return response.data;
  },

  // 音声合成（VOICEVOX TTS）
  synthesizeSpeech: async (text: string, youkaiId: string): Promise<string> => {
    const response = await axios.post(
      `${API_BASE_URL}/hazard/synthesize`,
      { text, youkai_id: youkaiId },
      { responseType: 'blob' }
    );
    return URL.createObjectURL(response.data);
  },

  // ヘルスチェック
  healthCheck: async (): Promise<{ status: string }> => {
    const response = await axios.get(`${API_BASE_URL}/hazard/health`);
    return response.data;
  }
};
