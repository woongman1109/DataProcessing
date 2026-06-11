%{ Organic Semiconductor Lab, SAINT, SKKU %}
%{ Source code copyright to Taewoong Yoon %}
%{ +++++ Email: TWYoon.rs@gmail.com +++++ %}
%{ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ %}
%{ ░░░░░░░█████░░░░███████░░██░░░░░░░░░░░ %}
%{ ░░░░░██░░░░░██░██░░░░░██░██░░░░░░░░░░░ %}
%{ ░░░░░█░░░░░░░█░███░░░░░░░██░░░░░░░░░░░ %}
%{ ░░░░░█░░░░░░░█░░░█████░░░██░░░░░░░░░░░ %}
%{ ░░░░░█░░░░░░░█░░░░░░░███░██░░░░░░░░░░░ %}
%{ ░░░░░██░░░░░██░██░░░░░██░██░░░░░█░░░░░ %}
%{ ░░░░░░░█████░░░░███████░░████████░░░░░ %}
%{ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ %}
%{ ++++++++++++++++++++++++++++++++++++++ %}

%{ ++++++++++++++ CODE FOR GIWAXS 3C BEAMLINE DATA ++++++++++++++ %}
% Automatically write an .xlsx file from .mat file with each variable in different sheet

%{
% ++++++++++++  R   E   A   D   M   E  ++++++++++++ %
 * .mat file should contain only the variables you need.
   Other variables in workspace MUST BE deleted.

 * (DATA NAME RULE) You should follow below rules when exporting your variables from raw data (.tif) with Matlab
   - Each variable should be named with its sample information
     (Required: Samplename, 1D vector direction)
   - 1D vector direction notation "MUST BE" qz or qxy
     Vector name rule: *qxy*, *qz* (case insensitive)
   - ex: P3HT_qxy, P3HT_qZ_2, P3HT_FeCl3_qxy_1 (left or right of qxy/qz can be any string)

 * (데이터 이름 규칙) Matlab으로 raw data에서 변수를 추출할 때 아래 규칙을 지켜야 합니다.
   - 각 변수는 샘플 정보로 이름을 붙여야 합니다.
     (필요 정보: 샘플 이름, 1D 벡터 방향)
   - 1D 벡터 방향은 "반드시" qxy 또는 qz로 표현해야 합니다.
     벡터 이름 규칙이 *qxy*, *qz*로 정해져 있습니다. (대소문자 구분 X)
   - 예시: P3HT_qxy, P3HT_qz_1, P3HT_FeCl3_qxy_1 (qxy/qz의 좌우로는 어떤 문자열이 와도 관계 없음)
%}

%{
% +++++++++++++++  Processing Step  +++++++++++++++ %
  1. Locate your .mat file in file explorer. Copy its name (with its filename extenstion).
  2. Paste the name into the designated position below (arked with comments).
  3. Run the program.
  * If the path of your .mat file is included in the path config, this file can make .xlsx in any path in your computer.
%}

% -------------------------------------------------------------------------------------------------------------


% >>>>> BELOW THIS LINE (1/2) <<<<<
Data = matfile("PI_GIWAXS_3C_1Dplot_Pristine.mat")
DataList = who(Data)
disp(DataList)

for i=1:length(DataList)
    % >>>>> BELOW THIS LINE (2/2) <<<<<
    xlswrite("PI_GIWAXS_3C_1Dplot_Pristine",Data.(DataList{i}),DataList{i},"A2")
end