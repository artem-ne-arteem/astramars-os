# AstraMars OS — установка рядом с Windows за несколько шагов.
#
# Запуск: PowerShell → irm https://artem-ne-arteem.github.io/astramars-os/install.ps1 | iex
#    или: скачайте AstraMars-Setup.cmd с сайта и откройте его.
#
# Что делает:
#   1. Проверяет компьютер: UEFI, BitLocker, свободное место, память, «Быстрый запуск».
#   2. Освобождает место на диске C: под AstraMars (сжимает раздел Windows; файлы не трогаются).
#   3. Скачивает установочный образ AstraMars OS и проверяет контрольную сумму.
#   4. Записывает его на флешку (флешка будет очищена — после явного подтверждения).
# Сама установка — после перезагрузки с флешки: выберите свободное место, Windows останется.

param([switch]$Preview, [string]$PreviewShot = "")

$ErrorActionPreference = "Stop"
$Repo = "artem-ne-arteem/astramars-os"
$Site = "https://artem-ne-arteem.github.io/astramars-os/"
$SelfUrl = $Site + "setup.ps1"
$MinGB = 40
$RecommendedGB = 60

# --- Права администратора ---------------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and -not $Preview) {
    # Запуск через «irm | iex» — файла нет, сохраняем себя во временную папку
    $self = $PSCommandPath
    if (-not $self) {
        $self = Join-Path $env:TEMP "AstraMars-Setup.ps1"
        $code = [Text.Encoding]::UTF8.GetString((New-Object Net.WebClient).DownloadData($SelfUrl)).TrimStart([char]0xFEFF)
        [IO.File]::WriteAllText($self, $code, (New-Object Text.UTF8Encoding $true))
    }
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$self`""
    return
}

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Add-Type -TypeDefinition @"
using System;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class RawDisk {
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern SafeFileHandle CreateFile(string name, uint access, uint share, IntPtr sec, uint disp, uint flags, IntPtr tmpl);
    // Открыть физический диск для записи (FileStream сам такие пути не открывает).
    // Сквозная запись (WRITE_THROUGH) без NO_BUFFERING — не нужна выровненная в памяти область.
    // Буфер FileStream 4096: записи по 4 МБ больше него и идут на диск напрямую.
    public static FileStream Open(int number) {
        return OpenPath(@"\\.\PhysicalDrive" + number);
    }
    public static FileStream OpenPath(string path) {
        SafeFileHandle h = CreateFile(path, 0xC0000000, 0x3, IntPtr.Zero, 3, 0x80000000, IntPtr.Zero);
        if (h.IsInvalid) throw new IOException("Не удалось открыть флешку для записи (код " + Marshal.GetLastWin32Error() + ")");
        return new FileStream(h, FileAccess.ReadWrite, 4096, false);
    }
}
"@

# --- Оформление ------------------------------------------------------------------------------
$Bg = [Drawing.Color]::FromArgb(0, 0, 0)
$Surface = [Drawing.Color]::FromArgb(18, 18, 18)
$Line = [Drawing.Color]::FromArgb(40, 40, 40)
$Fg = [Drawing.Color]::FromArgb(242, 242, 242)
$Muted = [Drawing.Color]::FromArgb(140, 140, 140)
$Accent = [Drawing.Color]::FromArgb(255, 59, 48)
$Ok = [Drawing.Color]::FromArgb(48, 209, 88)
$Warn = [Drawing.Color]::FromArgb(255, 159, 10)
$FontName = "Segoe UI"
function Font($size, $bold = $false) {
    New-Object Drawing.Font($FontName, $size, $(if ($bold) { [Drawing.FontStyle]::Bold } else { [Drawing.FontStyle]::Regular }))
}

$form = New-Object Windows.Forms.Form
$form.Text = "Установка AstraMars OS"
$form.ClientSize = New-Object Drawing.Size(760, 600)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedSingle"
$form.MaximizeBox = $false
$form.BackColor = $Bg
$form.ForeColor = $Fg
$form.Font = Font 10

function Label($text, $x, $y, $w, $h, $size = 10, $bold = $false, $color = $Fg) {
    $l = New-Object Windows.Forms.Label
    $l.Text = $text; $l.Location = New-Object Drawing.Point($x, $y); $l.Size = New-Object Drawing.Size($w, $h)
    $l.Font = Font $size $bold; $l.ForeColor = $color; $l.BackColor = [Drawing.Color]::Transparent
    return $l
}
function Button($text, $x, $y, $w, $primary = $false) {
    $b = New-Object Windows.Forms.Button
    $b.Text = $text; $b.Location = New-Object Drawing.Point($x, $y); $b.Size = New-Object Drawing.Size($w, 40)
    $b.FlatStyle = "Flat"; $b.Font = Font 10 $true; $b.Cursor = "Hand"
    $b.FlatAppearance.BorderSize = $(if ($primary) { 0 } else { 1 })
    $b.FlatAppearance.BorderColor = $Line
    $b.BackColor = $(if ($primary) { $Accent } else { $Surface }); $b.ForeColor = [Drawing.Color]::White
    return $b
}

# Шапка: точечное «ASTRAMARS» и номер шага
$header = Label "ASTRAMARS" 32 22 400 44 24 $true
$form.Controls.Add($header)
$stepLabel = Label "" 32 66 600 24 10 $false $Muted
$form.Controls.Add($stepLabel)
$dots = New-Object Windows.Forms.Panel
$dots.Location = New-Object Drawing.Point(560, 36); $dots.Size = New-Object Drawing.Size(170, 20)
$form.Controls.Add($dots)
$script:step = 0
$dots.Add_Paint({
    param($s, $e)
    $e.Graphics.SmoothingMode = "AntiAlias"
    for ($i = 0; $i -lt 5; $i++) {
        $c = if ($i -lt $script:step) { $Fg } elseif ($i -eq $script:step) { $Accent } else { $Line }
        $e.Graphics.FillEllipse((New-Object Drawing.SolidBrush $c), 10 + $i * 32, 4, 12, 12)
    }
})

$page = New-Object Windows.Forms.Panel
$page.Location = New-Object Drawing.Point(32, 100); $page.Size = New-Object Drawing.Size(696, 428)
$form.Controls.Add($page)
$back = Button "Назад" 32 540 120
$next = Button "Дальше" 568 540 160 $true
$form.Controls.Add($back); $form.Controls.Add($next)

$state = @{ freeGB = 0; unallocGB = 0; shrinkGB = $RecommendedGB; iso = ""; usb = $null; checks = @() }
$DownloadDir = Join-Path ([Environment]::GetFolderPath("UserProfile")) "Downloads\AstraMars"

function Clear-Page { $page.Controls.Clear() }
function Pump { [Windows.Forms.Application]::DoEvents() }

# --- Шаг 1. Проверка компьютера --------------------------------------------------------------
function Get-UnallocatedGB {
    # Самый большой неразмеченный участок на диске с Windows (если место уже освобождали)
    try {
        $num = (Get-Partition -DriveLetter C).DiskNumber
        $disk = Get-Disk -Number $num
        $parts = @(Get-Partition -DiskNumber $num | Sort-Object Offset)
        # Считаем в double: размеры дисков не помещаются в Int32, который PowerShell выбирает для Max
        $best = 0.0; $pos = [double]1MB
        foreach ($p in $parts) { $best = [math]::Max($best, [double]$p.Offset - $pos); $pos = [double]$p.Offset + [double]$p.Size }
        $best = [math]::Max($best, [double]$disk.Size - $pos - 1MB)
        return [math]::Floor($best / 1GB)
    } catch { return 0 }
}

function Get-Checks {
    $res = @()
    # UEFI: системный диск размечен GPT (на старых BIOS-компьютерах — MBR)
    try {
        $boot = Get-Disk | Where-Object IsBoot | Select-Object -First 1
        $uefi = $boot.PartitionStyle -eq "GPT"
    } catch { $uefi = $true }
    $res += ,@($(if ($uefi) { "ok" } else { "bad" }), "Режим загрузки UEFI",
        $(if ($uefi) { "Подходит" } else { "Компьютер загружается в старом режиме BIOS (MBR) — установка рядом с Windows не поддерживается" }))

    $sb = $null
    try { $sb = Confirm-SecureBootUEFI } catch { }
    $res += ,@("ok", "Безопасная загрузка (Secure Boot)",
        $(if ($sb) { "Включена — AstraMars загружается и с ней" } else { "Выключена — так тоже можно" }))

    $bl = $null
    try { $bl = (Get-BitLockerVolume -MountPoint "C:" -ErrorAction Stop).ProtectionStatus } catch { }
    $blOn = "$bl" -eq "On"
    $res += ,@($(if ($blOn) { "bad" } else { "ok" }), "Шифрование BitLocker",
        $(if ($blOn) { "Включено на диске C: — выключите его (Параметры → Конфиденциальность → Шифрование устройства) и запустите установщик снова" }
          else { "Выключено" }))

    $c = Get-Volume -DriveLetter C
    $state.freeGB = [math]::Floor($c.SizeRemaining / 1GB)
    $state.unallocGB = Get-UnallocatedGB
    if ($state.unallocGB -ge $MinGB) {
        $res += ,@("ok", "Место для AstraMars", "Уже освобождено $($state.unallocGB) ГБ — сжимать диск не нужно")
    } else {
        $enough = $state.freeGB -ge ($MinGB + 15)
        $msg = if ($enough) { "$($state.freeGB) ГБ — хватает" } else { "$($state.freeGB) ГБ — нужно хотя бы $($MinGB + 15) ГБ (AstraMars $MinGB ГБ + запас для Windows)" }
        $res += ,@($(if ($enough) { "ok" } else { "bad" }), "Свободно на диске C:", $msg)
    }

    $ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
    $msg = if ($ram -lt 4) { "$ram ГБ — будет медленно" } else { "$ram ГБ" }
    $res += ,@($(if ($ram -ge 4) { "ok" } else { "warn" }), "Оперативная память", $msg)

    $fast = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power" -Name HiberbootEnabled -ErrorAction SilentlyContinue).HiberbootEnabled
    $res += ,@($(if ($fast -eq 1) { "warn" } else { "ok" }), "«Быстрый запуск» Windows",
        $(if ($fast -eq 1) { "Включён — из AstraMars диск Windows будет только для чтения. Выключим его на шаге «Место»" } else { "Выключен" }))

    $net = $false
    try { $net = (Invoke-WebRequest "https://api.github.com" -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200 } catch { }
    $res += ,@($(if ($net) { "ok" } else { "bad" }), "Интернет", $(if ($net) { "Есть" } else { "Нет связи с GitHub — включите интернет или VPN" }))
    return $res
}

function Show-Checks {
    Clear-Page
    $script:step = 0; $dots.Invalidate()
    $stepLabel.Text = "Шаг 1 из 5 · Проверка компьютера"
    $page.Controls.Add((Label "Проверяю…" 0 0 600 30 14 $true))
    $next.Enabled = $false; $back.Visible = $false
    Pump
    $state.checks = Get-Checks
    Clear-Page
    $page.Controls.Add((Label "Проверка компьютера" 0 0 600 32 15 $true))
    $y = 48
    foreach ($c in $state.checks) {
        $dot = New-Object Windows.Forms.Panel
        $dot.Location = New-Object Drawing.Point(2, ($y + 6)); $dot.Size = New-Object Drawing.Size(10, 10)
        $col = switch ($c[0]) { "ok" { $Ok } "warn" { $Warn } default { $Accent } }
        $dot.BackColor = $col
        $page.Controls.Add($dot)
        $page.Controls.Add((Label $c[1] 24 $y 250 24 10.5 $true))
        $page.Controls.Add((Label $c[2] 280 $y 416 44 10 $false $Muted))
        $y += 46
    }
    $bad = @($state.checks | Where-Object { $_[0] -eq "bad" }).Count
    $next.Enabled = ($bad -eq 0) -or $Preview
    if ($bad) { $page.Controls.Add((Label "Исправьте пункты с красной точкой и запустите установщик снова." 0 ($y + 6) 696 24 10 $true $Accent)) }
}

# --- Шаг 2. Место на диске ----------------------------------------------------------------------
function Show-Space {
    Clear-Page
    $script:step = 1; $dots.Invalidate()
    $stepLabel.Text = "Шаг 2 из 5 · Место для AstraMars"
    $back.Visible = $true; $next.Enabled = $true
    if ($state.unallocGB -ge $MinGB) {
        $state.shrinkGB = $state.unallocGB
        $page.Controls.Add((Label "Место уже есть" 0 0 600 32 15 $true))
        $page.Controls.Add((Label "$($state.unallocGB) ГБ" 0 50 300 60 30 $true))
        $page.Controls.Add((Label ("На диске уже освобождено $($state.unallocGB) ГБ — AstraMars встанет туда. " +
            "Сжимать раздел Windows не нужно.") 0 120 696 48 10.5 $false $Muted))
        $script:fastBox = $null
        $next.Text = "Дальше"
        return
    }
    $part = Get-Partition -DriveLetter C
    try { $sup = Get-PartitionSupportedSize -DriveLetter C -ErrorAction Stop }
    catch { $sup = @{ SizeMin = $part.Size - ($state.freeGB - 5) * 1GB } }   # просмотр без прав администратора
    $maxGB = [int]([math]::Floor(([double]$part.Size - [double]$sup.SizeMin) / 1GB) - 10)
    $maxGB = [int][math]::Min([double]$maxGB, [double]($state.freeGB - 15))
    $page.Controls.Add((Label "Сколько места отдать AstraMars" 0 0 600 32 15 $true))
    $page.Controls.Add((Label ("Раздел Windows (C:) станет меньше — файлы и программы Windows не пострадают. " +
        "Рекомендуем $RecommendedGB ГБ и больше, если будете ставить игры.") 0 40 696 48 10 $false $Muted))
    if ($maxGB -lt $MinGB) {
        $page.Controls.Add((Label ("Windows разрешает освободить только $([math]::Max($maxGB,0)) ГБ: мешают неперемещаемые файлы " +
            "(файл подкачки, гибернация, точки восстановления). Отключите гибернацию (powercfg /h off), перезагрузитесь " +
            "и запустите установщик снова.") 0 110 696 90 10.5 $true $Accent))
        $next.Enabled = $false
        return
    }
    $big = Label "" 0 100 300 60 30 $true
    $page.Controls.Add($big)
    $bar = New-Object Windows.Forms.TrackBar
    $bar.Location = New-Object Drawing.Point(0, 170); $bar.Size = New-Object Drawing.Size(696, 45)
    $bar.Minimum = $MinGB; $bar.Maximum = $maxGB; $bar.TickFrequency = 10
    $bar.Value = [math]::Min([math]::Max($state.shrinkGB, $MinGB), $maxGB)
    $bar.BackColor = $Bg
    $update = { $state.shrinkGB = $bar.Value; $big.Text = "$($bar.Value) ГБ" }
    $bar.Add_ValueChanged($update); & $update
    $page.Controls.Add($bar)
    $page.Controls.Add((Label "от $MinGB ГБ" 0 220 200 22 9 $false $Muted))
    $page.Controls.Add((Label "до $maxGB ГБ" 596 220 100 22 9 $false $Muted))

    $fast = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power" -Name HiberbootEnabled -ErrorAction SilentlyContinue).HiberbootEnabled
    $script:fastBox = New-Object Windows.Forms.CheckBox
    $fastBox.Text = "Выключить «Быстрый запуск» Windows (чтобы из AstraMars можно было работать с файлами Windows)"
    $fastBox.Location = New-Object Drawing.Point(0, 270); $fastBox.Size = New-Object Drawing.Size(696, 40)
    $fastBox.Checked = $fast -eq 1; $fastBox.Visible = $fast -eq 1; $fastBox.ForeColor = $Fg
    $page.Controls.Add($fastBox)
    $next.Text = "Освободить место"
}

function Do-Shrink {
    if ($state.unallocGB -ge $MinGB) { Show-Download; return }
    $next.Enabled = $false; $back.Enabled = $false; $next.Text = "Сжимаю…"; Pump
    try {
        if ($fastBox -and $fastBox.Checked) {
            Set-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power" -Name HiberbootEnabled -Value 0
        }
        $part = Get-Partition -DriveLetter C
        if (-not $Preview) { Resize-Partition -DriveLetter C -Size ($part.Size - [int64]$state.shrinkGB * 1GB) }
        [Windows.Forms.MessageBox]::Show("Готово: освобождено $($state.shrinkGB) ГБ.", "AstraMars") | Out-Null
        $next.Text = "Дальше"; $back.Enabled = $true
        Show-Download
    } catch {
        [Windows.Forms.MessageBox]::Show("Windows не дала сжать раздел: $($_.Exception.Message)`n`nПопробуйте меньше места, " +
            "или отключите гибернацию (powercfg /h off) и перезагрузитесь.", "AstraMars", "OK", "Warning") | Out-Null
        $next.Text = "Освободить место"; $next.Enabled = $true; $back.Enabled = $true
    }
}

# --- Шаг 3. Скачивание образа --------------------------------------------------------------------
function Show-Download {
    Clear-Page
    $script:step = 2; $dots.Invalidate()
    $stepLabel.Text = "Шаг 3 из 5 · Скачивание AstraMars OS"
    $next.Text = "Скачать"; $next.Enabled = $true
    $page.Controls.Add((Label "Установочный образ AstraMars OS" 0 0 600 32 15 $true))
    $page.Controls.Add((Label "Около 4–5 ГБ. Сохраняется в папку «Загрузки\AstraMars», докачивается при обрыве." 0 40 696 40 10 $false $Muted))
    $script:dlBar = New-Object Windows.Forms.ProgressBar
    $dlBar.Location = New-Object Drawing.Point(0, 110); $dlBar.Size = New-Object Drawing.Size(696, 14); $dlBar.Visible = $false
    $page.Controls.Add($dlBar)
    $script:dlText = Label "" 0 134 696 60 10 $false $Muted
    $page.Controls.Add($dlText)
}

function Do-Download {
    $next.Enabled = $false; $back.Enabled = $false; $dlBar.Visible = $true
    try {
        $dlText.Text = "Узнаю последнюю версию…"; Pump
        $rel = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/tags/iso-latest" -Headers @{ "User-Agent" = "AstraMars-Setup" }
        $parts = @($rel.assets | Where-Object { $_.name -match '\.iso\.part\d+$' } | Sort-Object name)
        $sumAsset = $rel.assets | Where-Object { $_.name -like "*.iso.sha256" } | Select-Object -First 1
        if (-not $parts) { throw "в релизе нет образа" }
        $isoName = $parts[0].name -replace '\.part\d+$', ''
        New-Item -ItemType Directory -Force $DownloadDir | Out-Null
        $iso = Join-Path $DownloadDir $isoName
        $total = ($parts | Measure-Object size -Sum).Sum
        $expected = ([Text.Encoding]::ASCII.GetString((New-Object Net.WebClient).DownloadData($sumAsset.browser_download_url))).Trim().Split()[0].ToLower()
        # Уже скачанный образ годится, только если совпадает контрольная сумма новой версии
        if ((Test-Path $iso) -and (Get-Item $iso).Length -eq $total) {
            $dlText.Text = "Проверяю уже скачанный образ…"; Pump
            if ((Get-FileHash $iso -Algorithm SHA256).Hash.ToLower() -ne $expected) { Remove-Item $iso }
        }
        if (-not (Test-Path $iso)) {
            # Части от прошлой версии с теми же именами не годятся — удаляем
            Get-ChildItem $DownloadDir -Filter "*.iso.part*" -ErrorAction SilentlyContinue | Where-Object {
                $name = $_.Name; -not ($parts | Where-Object { $_.name -eq $name -and $_.size -eq (Get-Item (Join-Path $DownloadDir $name)).Length })
            } | Remove-Item -ErrorAction SilentlyContinue
            $done = 0
            foreach ($p in $parts) {
                $dst = Join-Path $DownloadDir $p.name
                if (-not (Test-Path $dst) -or (Get-Item $dst).Length -ne $p.size) {
                    $job = Start-BitsTransfer -Source $p.browser_download_url -Destination $dst -Asynchronous -DisplayName "AstraMars"
                    while ($job.JobState -in "Transferring", "Connecting", "Queued", "TransientError") {
                        $pct = [int](($done + $job.BytesTransferred) * 100 / $total)
                        $dlBar.Value = [math]::Min($pct, 100)
                        $dlText.Text = "Скачано $([math]::Round(($done + $job.BytesTransferred) / 1GB, 2)) из $([math]::Round($total / 1GB, 2)) ГБ"
                        Pump; Start-Sleep -Milliseconds 300
                    }
                    if ($job.JobState -ne "Transferred") { $err = $job.ErrorDescription; Remove-BitsTransfer $job; throw "загрузка прервалась: $err" }
                    Complete-BitsTransfer $job
                }
                $done += $p.size
            }
            $dlText.Text = "Собираю образ из частей…"; Pump
            $out = [IO.File]::Create($iso)
            foreach ($p in $parts) { $in = [IO.File]::OpenRead((Join-Path $DownloadDir $p.name)); $in.CopyTo($out); $in.Close() }
            $out.Close()
        }
        $dlText.Text = "Проверяю контрольную сумму…"; $dlBar.Value = 100; Pump
        $hash = (Get-FileHash $iso -Algorithm SHA256).Hash.ToLower()
        if ($hash -ne $expected) {
            Remove-Item $iso
            foreach ($p in $parts) { Remove-Item (Join-Path $DownloadDir $p.name) -ErrorAction SilentlyContinue }
            throw "образ повреждён при скачивании — запустите скачивание снова" }
        foreach ($p in $parts) { Remove-Item (Join-Path $DownloadDir $p.name) -ErrorAction SilentlyContinue }
        $state.iso = $iso
        Show-Usb
    } catch {
        $dlText.Text = "Не получилось: $($_.Exception.Message)"
        $dlText.ForeColor = $Accent
        $next.Text = "Скачать снова"; $next.Enabled = $true
    }
    $back.Enabled = $true
}

# --- Шаг 4. Флешка -----------------------------------------------------------------------------------
function Show-Usb {
    Clear-Page
    $script:step = 3; $dots.Invalidate()
    $stepLabel.Text = "Шаг 4 из 5 · Флешка"
    $next.Text = "Записать"; $next.Enabled = $false
    $page.Controls.Add((Label "Вставьте флешку на 8 ГБ или больше" 0 0 600 32 15 $true))
    $page.Controls.Add((Label "Всё, что на ней есть, будет удалено." 0 40 696 24 10.5 $true $Accent))
    $script:usbList = New-Object Windows.Forms.ListBox
    $usbList.Location = New-Object Drawing.Point(0, 80); $usbList.Size = New-Object Drawing.Size(696, 130)
    $usbList.BackColor = $Surface; $usbList.ForeColor = $Fg; $usbList.BorderStyle = "FixedSingle"; $usbList.Font = Font 11
    $page.Controls.Add($usbList)
    $refresh = Button "Обновить список" 0 222 180
    $page.Controls.Add($refresh)
    $script:usbText = Label "" 0 280 696 80 10 $false $Muted
    $page.Controls.Add($usbText)
    $script:disks = @()
    $fill = {
        $usbList.Items.Clear()
        $isoSize = if ($state.iso) { (Get-Item $state.iso).Length } else { 6GB }
        $script:disks = @(Get-Disk | Where-Object { $_.BusType -eq "USB" -and -not $_.IsBoot -and -not $_.IsSystem -and $_.Size -ge $isoSize })
        foreach ($d in $script:disks) { [void]$usbList.Items.Add("$($d.FriendlyName) — $([math]::Round($d.Size / 1GB, 1)) ГБ") }
        if (-not $script:disks) { $usbText.Text = "Флешка не найдена. Вставьте её и нажмите «Обновить список»." }
        else { $usbText.Text = "" }
    }
    $refresh.Add_Click($fill)
    $usbList.Add_SelectedIndexChanged({ $next.Enabled = $usbList.SelectedIndex -ge 0 })
    & $fill
}

function Do-Write {
    $d = $script:disks[$usbList.SelectedIndex]
    $answer = [Windows.Forms.MessageBox]::Show(
        "Все данные на «$($d.FriendlyName)» ($([math]::Round($d.Size / 1GB, 1)) ГБ) будут удалены. Продолжить?",
        "AstraMars", "YesNo", "Warning")
    if ($answer -ne "Yes") { return }
    $next.Enabled = $false; $back.Enabled = $false
    $bar = New-Object Windows.Forms.ProgressBar
    $bar.Location = New-Object Drawing.Point(0, 380); $bar.Size = New-Object Drawing.Size(696, 14)
    $page.Controls.Add($bar)
    try {
        $usbText.Text = "Очищаю флешку…"; Pump
        if (-not $Preview) {
            Set-Disk -Number $d.Number -IsReadOnly $false -ErrorAction SilentlyContinue
            Clear-Disk -Number $d.Number -RemoveData -RemoveOEM -Confirm:$false -ErrorAction SilentlyContinue
            $src = [IO.File]::OpenRead($state.iso)
            $dst = [RawDisk]::Open($d.Number)
            $buf = New-Object byte[] (4MB)
            $total = $src.Length; $written = 0
            while (($n = $src.Read($buf, 0, $buf.Length)) -gt 0) {
                $len = [int]([math]::Ceiling($n / 4096) * 4096)     # запись целыми секторами
                if ($len -gt $n) { [Array]::Clear($buf, $n, $len - $n) }
                $dst.Write($buf, 0, $len)
                $written += $n
                $bar.Value = [int]($written * 100 / $total)
                $usbText.Text = "Записываю: $([math]::Round($written / 1GB, 2)) из $([math]::Round($total / 1GB, 2)) ГБ"
                Pump
            }
            $dst.Flush(); $dst.Close(); $src.Close()
            Update-Disk -Number $d.Number -ErrorAction SilentlyContinue
        }
        Show-Done
    } catch {
        $usbText.Text = "Не получилось записать: $($_.Exception.Message). Можно записать образ из «Загрузки\AstraMars» программой Rufus (режим DD)."
        $usbText.ForeColor = $Accent
        $next.Enabled = $true; $back.Enabled = $true
    }
}

# --- Шаг 5. Готово -------------------------------------------------------------------------------------
function Show-Done {
    Clear-Page
    $script:step = 4; $dots.Invalidate()
    $stepLabel.Text = "Шаг 5 из 5 · Установка"
    $page.Controls.Add((Label "Всё готово к установке" 0 0 600 32 15 $true))
    $steps = @(
        "Не вынимайте флешку и перезагрузите компьютер.",
        "Сразу при включении нажимайте клавишу меню загрузки: F12, F11, F8 или Esc (зависит от компьютера) и выберите флешку.",
        "В установщике выберите язык, затем «Место установки» → свободное место (те $($state.shrinkGB) ГБ). Раздел Windows не трогайте.",
        "После установки при включении появится меню: AstraMars OS или Windows."
    )
    $y = 50
    for ($i = 0; $i -lt $steps.Count; $i++) {
        $page.Controls.Add((Label ("0" + ($i + 1)) 0 $y 40 30 14 $true $Accent))
        $page.Controls.Add((Label $steps[$i] 48 ($y + 2) 648 52 10.5))
        $y += 64
    }
    $page.Controls.Add((Label "Подробная инструкция и помощь: $Site" 0 ($y + 8) 696 24 9.5 $false $Muted))
    $back.Visible = $false
    $next.Text = "Перезагрузить"; $next.Enabled = $true
}

$next.Add_Click({
    switch ($script:step) {
        0 { Show-Space }
        1 { Do-Shrink }
        2 { Do-Download }
        3 { Do-Write }
        4 { if (-not $Preview) { Restart-Computer -Force } else { $form.Close() } }
    }
})
$back.Add_Click({
    switch ($script:step) {
        1 { $next.Text = "Дальше"; Show-Checks }
        2 { Show-Space }
        3 { Show-Download }
    }
})

$form.Add_Shown({
    Show-Checks
    if ($PreviewShot) {
        # Только для проверки внешнего вида: снимок окна каждого шага
        foreach ($s in 0, 1, 2, 3, 4) {
            switch ($s) { 1 { Show-Space } 2 { Show-Download } 3 { Show-Usb } 4 { Show-Done } }
            Pump
            $bmp = New-Object Drawing.Bitmap($form.Width, $form.Height)
            $form.DrawToBitmap($bmp, (New-Object Drawing.Rectangle(0, 0, $form.Width, $form.Height)))
            $bmp.Save("$PreviewShot-$s.png")
        }
        $form.Close()
    }
})
[void]$form.ShowDialog()
