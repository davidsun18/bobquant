```markdown                                                               
  # MEMORY_CONFIG.md - 全局记忆系统配置                                   
                                                                          
  ## 🧠 记忆系统架构                                                      
                                                                          
  ### 核心配置                                                            
  ```json                                                                 
  {                                                                       
    "memory": {                                                           
      "enabled": true,                                                    
      "enableRetrieval": true,                                            
      "topK": 5,                                                          
      "similarityThreshold": 0.75,                                        
      "storagePath": "~/.openclaw/workspace-content/memory/",             
      "indexType": "vector",                                              
      "embeddingModel": "bge-large-zh"                                    
    }                                                                     
  }                                                                       
```                                                                       
                                                                          
### 记忆层级                                                              
                                                                          
| 层级 | 存储位置 | 用途 | 保留策略 |                                     
|------|---------|------|------- --|                                      
| 短期记忆 | memory/daily/ | 每日工作日志 | 保留 30 天 |                  
| 长期记忆 | MEMORY.md | 重要决策与发现 | 永久保留 |                      
| 共享知识 | knowledge/ | 团队共享文档 | 永久保留 |                       
| 向量索引 | memory/index/ | 检索增强 | 自动更新 |                        
                                                                          
### 检索配置                                                              
                                                                          
检索参数：                                                                
- topK: 5 - 每次检索返回最相关的 5 条记忆                                 
- similarityThreshold: 0.75 - 相似度阈值，低于此值不返回                  
- recencyBoost: 0.1 - 近期记忆加权系数                                    
                                                                          
检索触发条件：                                                            
- 用户问题包含历史上下文引用                                              
- 任务类型与历史记录匹配                                                  
- Boss Bot 进行综合决策时                                                 
                                                                          
📂 存储路径                                                               
                                                                          
```                                                                       
  ~/.openclaw/workspace-content/                                          
  ├── memory/                                                             
  │   ├── daily/           # 每日记忆                                     
  │   │   ├── 2026-04-18.md                                               
  │   │   └── ...                                                         
  │   ├── index/           # 向量索引                                     
  │   │   ├── embeddings/                                                 
  │   │   └── metadata/                                                   
  │   └── archive/         # 归档记忆                                     
  ├── knowledge/           # 共享知识库                                   
  │   ├── strategies/      # 策略文档                                     
  │   ├── factors/         # 因子库                                       
  │   ├── backtests/       # 回测记录                                     
  │   └── logs/            # 交易日志                                     
  └── MEMORY.md            # 长期记忆汇总                                 
```                                                                       
                                                                          
🔄 记忆写入规则                                                           
                                                                          
### 自动写入                                                              
                                                                          
- 每个任务完成后，执行 Agent 自动写入关键信息                             
- Boss Bot 汇总决策结果后写入 MEMORY.md                                   
- 每日 17:00 自动归档当日记忆                                             
                                                                          
### 手动写入                                                              
                                                                          
- Agent 发现重要洞察时可主动写入                                          
- 用户可手动添加备注到 MEMORY.md                                          
                                                                          
### 记忆格式                                                              
                                                                          
```markdown                                                               
  ## [日期] [Agent] [主题]                                                
                                                                          
  **内容：** ...                                                          
                                                                          
  **标签：** #因子挖掘 #动量策略 #A 股                                    
                                                                          
  **关联任务：** [任务 ID]                                                
                                                                          
  **重要程度：** ⭐⭐⭐⭐                                                 
```                                                                       
                                                                          
``` 
