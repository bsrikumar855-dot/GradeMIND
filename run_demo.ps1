$ErrorActionPreference = "Continue"

$startTime = Get-Date

Write-Host "Running 1. verify_demo"
$sw1 = [System.Diagnostics.Stopwatch]::StartNew()
python -m scripts.verify_demo --offline *> tmp\out1.txt
$sw1.Stop()

Write-Host "Running 2. grade DL"
$sw2 = [System.Diagnostics.Stopwatch]::StartNew()
python -m scripts.grade --paper backend/storage/question_papers/a73e49ab-c18b-499d-85cd-6cc82a186ee8/S_571ac7e774c5067a.pdf --answers backend/storage/answer_sheets/a73e49ab-c18b-499d-85cd-6cc82a186ee8/S_ebaff77e80f0eb33.pdf --scheme schemes/dl-2026-s1.json --out tmp/demo_dl --mask 0,0,1,0.15 --max-pages 3 --offline *> tmp\out2.txt
$sw2.Stop()

Write-Host "Running 3. grade DSA"
$sw3 = [System.Diagnostics.Stopwatch]::StartNew()
python -m scripts.grade --paper "$HOME/Downloads/WhatsApp Image 2026-08-14 at 2.42.46 PM.jpeg" --answers "$HOME/Downloads/WhatsApp Image 2026-08-14 at 2.42.46 PM (1).jpeg" --scheme schemes/dsa-2026-cse201.json --out tmp/demo_dsa --mask 0,0,1,0.03 --offline *> tmp\out3.txt
$sw3.Stop()

Write-Host "Running 4. demo_marking"
$sw4 = [System.Diagnostics.Stopwatch]::StartNew()
python -m scripts.demo_marking *> tmp\out4.txt
$sw4.Stop()

$endTime = Get-Date
$totalTime = $endTime - $startTime

Write-Host "Total time: $($totalTime.TotalSeconds) seconds"
Write-Host "Times: 1=$($sw1.Elapsed.TotalSeconds), 2=$($sw2.Elapsed.TotalSeconds), 3=$($sw3.Elapsed.TotalSeconds), 4=$($sw4.Elapsed.TotalSeconds)"
