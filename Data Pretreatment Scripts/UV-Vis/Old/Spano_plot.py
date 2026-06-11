import numpy as np
import matplotlib.pyplot as plt

# 임의의 파라미터 설정 (사용자는 실제 값으로 수정 필요)
S = 1.0
W = 0.2
E_p = 0.17
sigma = 0.05
hbar = 1.05457182e-34 # h/2pi
E00 = 2
C = 0.001

# w 범위 설정
w = np.linspace(1.2, 3.5, 500)  # 필요에 따라 수정

# 주어진 식을 각 항으로 분해해서 계산

# 공통항
prefactor1 = np.exp(-S)
factor = 1/(sigma*np.sqrt(2*np.pi))

term1 = (prefactor1) * (1 - (W*np.exp(-S)/(2*E_p)*1.3171))**2 * factor \
         * np.exp(-((hbar*w - E00 - 0.5*W*np.exp(-S))**2)/(2*sigma**2))

term2 = (prefactor1 * S) * (1 - (W*np.exp(-S)/(2*E_p)*(-0.5365)))**2 * factor \
         * np.exp(-((hbar*w - E00 - E_p - 0.5*W*S*np.exp(-S))**2)/(2*sigma**2))

term3 = (prefactor1 * S**2 / 2) * (1 - (W*np.exp(-S)/(2*E_p)*(-2.1523)))**2 * factor \
         * np.exp(-((hbar*w - E00 - 2*E_p - 0.5*W*S**2*np.exp(-S))**2)/(2*sigma**2))

term4 = (prefactor1 * S**3 / 6) * (1 - (W*np.exp(-S)/(2*E_p)*(-7.2749)))**2 * factor \
         * np.exp(-((hbar*w - E00 - 3*E_p - 0.5*W*S**3*np.exp(-S))**2)/(2*sigma**2))

term5 = (prefactor1 * S**4 / 24) * (1 - (W*np.exp(-S)/(2*E_p)*(-44.5369)))**2 * factor \
         * np.exp(-((hbar*w - E00 - 4*E_p - 0.5*W*S**4*np.exp(-S))**2)/(2*sigma**2))


# 총합
total = C*(term1 + term2 + term3 + term4 + term5)

# 그래프 표시
plt.figure(figsize=(10,6))
plt.plot(w, total, label="Total Expression")
plt.title("Plot of the Given Complex Expression", fontsize=16)
plt.xlabel("w", fontsize=14)
plt.ylabel("Value", fontsize=14)
plt.legend(fontsize=12)
plt.grid(alpha=0.3)
plt.show()
