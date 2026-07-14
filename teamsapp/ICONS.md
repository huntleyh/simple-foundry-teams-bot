# Teams App Icons

Place two PNG files here before packaging:

| File | Size | Purpose |
|------|------|---------|
| `color.png` | 192×192 px | Full-colour app icon shown in Teams |
| `outline.png` | 32×32 px | White/transparent outline icon for the app bar |

## Quick placeholder icons (PowerShell)

If you just need something to sideload quickly, generate minimal solid-colour PNGs:

```powershell
Add-Type -AssemblyName System.Drawing

# color.png — 192x192 blue square
$bmp = New-Object System.Drawing.Bitmap 192,192
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::FromArgb(0,120,212))
$bmp.Save("$PSScriptRoot\color.png", [System.Drawing.Imaging.ImageFormat]::Png)

# outline.png — 32x32 white square
$bmp2 = New-Object System.Drawing.Bitmap 32,32
$g2 = [System.Drawing.Graphics]::FromImage($bmp2)
$g2.Clear([System.Drawing.Color]::White)
$bmp2.Save("$PSScriptRoot\outline.png", [System.Drawing.Imaging.ImageFormat]::Png)
```

Both `.png` files are gitignored — add your real icons before packaging.
