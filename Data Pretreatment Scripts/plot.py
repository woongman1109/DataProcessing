import pandas as pd
import matplotlib.pyplot as plt

# 엑셀 파일 읽기 (파일 경로를 적절히 수정하세요)
file_path = "C:/Users/woong/Dropbox/==== SKKU-SAINT ====/==== SAINT-OSL ====/3. My/Lab etc/Programming/Data Pretreatment Scripts/UV-Vis/data.xlsx"  # 파일 경로를 여기에 입력
data = pd.read_excel(file_path)

# 데이터의 첫 번째 열을 x축, 두 번째 열을 y축으로 설정
x = data.iloc[:, 0]  # 첫 번째 열
y = data.iloc[:, 1]  # 두 번째 열

# 그래프 그리기
plt.figure(figsize=(10, 6))
plt.plot(x, y, marker='o', markersize=2, linewidth=1, label="Data")
plt.xlabel("Wavelength (nm)", fontsize=14)
plt.ylabel("Abs (a.u.)", fontsize=14)
plt.grid(alpha=0.3)
plt.legend()
plt.show()