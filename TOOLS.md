# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## 📦 BobQuant 配置

### GitHub 仓库
- **仓库名**: `bobquant` (不是 bob-quant!)
- **URL**: https://github.com/davidsun18/bobquant.git
- **Token**: `REDACTED` ✅ 长期有效
- **分支**: `main`

### 推送命令
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
git push origin main
```

### 数据源
- **主数据源**: 腾讯财经 (稳定，100ms 响应)
- **历史数据**: baostock
- **已禁用**: iTick (DNS 问题)

### 交易时段
- 早盘：09:25 - 11:35
- 午盘：12:55 - 15:05

### 监控
- 日志：`sim_trading/模拟盘日志.log`
- 进程：`ps aux | grep "python3 main.py"`

---

Add whatever helps you do your job. This is your cheat sheet.
