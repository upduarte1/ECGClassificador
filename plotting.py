import numpy as np
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import io

def show_ecg_plot(signal, sampling_frequency=300, signal_id=None, duration=30):
  
  signal = np.array(signal, dtype=float)
  signal = signal[np.isfinite(signal)]
  if len(signal) == 0:
      st.warning(f"ECG signal ID {signal_id} is empty or invalid.")
      return
  samples_to_show = int(duration * sampling_frequency)
  signal = signal[:samples_to_show]
  # Escala: 25 mm/s → ≈ 0.984 inch/s, para 10 segundos → ~9.84 inches
  mm_per_second = 25
  dpi = 300
  inches_per_second = mm_per_second / 25.4
  width_in_inches = 10 * inches_per_second  # Cada faixa = 10s
  height_in_inches = 2  # Altura de cada faixa        
  fig, axs = plt.subplots(3, 1, figsize=(width_in_inches, height_in_inches * 3), dpi=dpi, sharey=True)
  for i in range(3):
      start = i * 10 * sampling_frequency
      end = (i + 1) * 10 * sampling_frequency
      s_segment = signal[start:end]
      t_segment = np.arange(len(s_segment)) / sampling_frequency
      ax = axs[i]
      ax.plot(t_segment + i * 10, s_segment, color='black', linewidth=0.8)
      ax.set_xlim([0, 10])
      ax.set_xlim([i * 10, (i + 1) * 10])
      ax.set_ylim([-1500, 1500])                
      ax.set_facecolor("white")        
      ax.set_xticks(np.arange(i * 10, (i + 1) * 10 + 1, 1))
      ax.set_yticks(np.arange(-1500, 1601, 500))
      ax.set_yticklabels([])
      if i == 2:
          ax.set_xlabel("Tempo (s)")
      if i == 1:
          ax.set_ylabel("ECG (μV)")
      for j in np.arange(i * 10, (i + 1) * 10, 0.2):  # vertical grid lines (5mm = 0.2s)
          ax.axvline(j, color='red', linewidth=0.5, alpha=0.3)
      for j in np.arange(i * 10, (i + 1) * 10, 0.04):  # vertical grid lines (1mm = 0.04s)
          ax.axvline(j, color='red', linewidth=0.5, alpha=0.1)
      for j in np.arange(-1500, 1600, 500):  # 5 mm = 0.5 mV = 500 μV
          ax.axhline(j, color='red', linewidth=0.5, alpha=0.3)
      for j in np.arange(-1500, 1600, 100):  # 1 mm = 0.1 mV = 100 μV
          ax.axhline(j, color='red', linewidth=0.5, alpha=0.1)
  fig.suptitle(f"ECG Signal ID {signal_id}" if signal_id else "ECG Signal", fontsize=14)
  plt.tight_layout()
  # Mostrar imagem com qualidade ideal
  buf = io.BytesIO()
  fig.savefig(buf, format="png", dpi=dpi, bbox_inches='tight')
  buf.seek(0)
  st.image(buf, use_container_width=True)
