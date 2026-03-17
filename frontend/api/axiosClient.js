import axios from 'axios';

// Framework'üne uygun olan değişkeni buradan çekiyoruz. 
// Örnekte Next.js veya Vite yapıları gösterilmiştir:
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || import.meta.env.VITE_API_URL;

// Sadece bu projeye özel, ayarlanmış bir axios örneği yaratıyoruz
const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    // İleride token eklersen buraya merkezi olarak koyabilirsin
  },
});

export default apiClient;