import { useState } from 'react'
import AsyncSelect from 'react-select/async'
import type { SingleValue } from 'react-select'

import apiClient from '../api/axiosClient.ts'

type CariOption = {
  value: string
  label: string
}

type CariApiItem = {
  cari_kod: string
  cari_unvan: string
}

function CariAramaSelect() {
  const [secilenCari, setSecilenCari] = useState<CariOption | null>(null)

  const carileriGetir = async (inputValue: string): Promise<CariOption[]> => {
    if (!inputValue || inputValue.length < 2) {
      return []
    }

    try {
      const response = await apiClient.get<CariApiItem[]>('/cariler', {
        params: { arama_kriteri: inputValue },
      })

      return response.data.map((cari) => ({
        value: cari.cari_kod,
        label: `${cari.cari_kod} - ${cari.cari_unvan}`,
      }))
    } catch (error) {
      console.error('Cari verileri cekilirken hata olustu:', error)
      return []
    }
  }

  const handleCariSecimi = (option: SingleValue<CariOption>) => {
    setSecilenCari(option)
  }

  return (
    <div style={{ width: 'min(480px, 90vw)' }}>
      <AsyncSelect<CariOption, false>
        cacheOptions
        defaultOptions={false}
        loadOptions={carileriGetir}
        onChange={handleCariSecimi}
        value={secilenCari}
        placeholder="Cari kodu veya unvanı ile ara"
        noOptionsMessage={({ inputValue }) =>
          inputValue.length < 2 ? 'En az 2 karakter girin' : 'Sonuc bulunamadi'
        }
      />
    </div>
  )
}

export default CariAramaSelect