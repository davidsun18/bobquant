```markdown                                                               
  # MODEL_CONFIG.md - 模型偏好配置                                        
                                                                          
  ## 🤖 模型配置                                                          
                                                                          
  ### 模型选择策略                                                        
                                                                          
  | 任务类型 | 推荐模型 | 优先级 | 说明 |                                 
  |---------|---------|--------|-- ----|                                  
  | 策略研发 | qwen3.5-plus | 高 | 高推理能力，复杂分析 |                 
  | 因子挖掘 | qwen3.5-plus | 高 | 需要深度分析 |                         
  | 回测分析 | qwen3.5-plus | 高 | 统计分析与解读 |                       
  | 数据采集 | qwen2.5-plus | 中 | 简单任务，性价比优先 |                 
  | 数据清洗 | qwen2.5-plus | 中 | 规则明确，无需复杂推理 |               
  | 代码开发 | qwen3.5-plus | 高 | 需要逻辑严谨 |                         
  | 报告生成 | qwen2.5-plus | 中 | 格式化输出，成本敏感 |                 
  | 合规检查 | qwen3.5-plus | 高 | 风险敏感，需准确判断 |                 
  | 日常对话 | qwen2.5-plus | 低 | 简单交互，成本优先 |                   
                                                                          
  ### 模型参数                                                            
                                                                          
  ```json                                                                 
  {                                                                       
    "models": {                                                           
      "high_reasoning": {                                                 
        "name": "qwen3.5-plus",                                           
        "use_cases": ["策略研发", "因子挖掘", "回测分析", "代码开发",     
"合规检查"],                                                              
        "max_tokens": 32000,                                              
        "temperature": 0.3                                                
      },                                                                  
      "cost_effective": {                                                 
        "name": "qwen2.5-plus",                                           
        "use_cases": ["数据采集", "数据清洗", "报告生成", "日常对话"],    
        "max_tokens": 16000,                                              
        "temperature": 0.5                                                
      }                                                                   
    }                                                                     
  }                                                                       
```                                                                       
                                                                          
### 成本优化策略                                                          
                                                                          
任务分级：                                                                
- 高优先级 - 策略、风控、核心代码 → 使用高推理模型                        
- 中优先级 - 数据处理、报告 → 使用性价比模型                              
- 低优先级 - 日常交互 → 使用基础模型                                      
                                                                          
Token 预算：                                                              
| Agent | 日预算 | 月预算 | 说明 |                                        
|-------|--------|--------|----- -|                                       
| Boss Bot | 50k | 1M | 任务分发与汇总 |                                  
| Quant Research Bot | 100k | 2M | 策略研发 |                             
| Data Bot | 20k | 400k | 数据处理 |                                      
| Dev Bot | 50k | 1M | 代码开发 |                                         
| Execution Bot | 20k | 400k | 交易执行 |                                 
| Compliance Bot | 30k | 600k | 合规检查 |                                
| Report Bot | 30k | 600k | 报告生成 |                                    
                                                                          
总计月预算：约 6M tokens                                                  
                                                                          
### 模型切换规则                                                          
                                                                          
自动切换：                                                                
- 任务复杂度 > 阈值 → 切换到高推理模型                                    
- Token 使用接近预算 → 切换到性价比模型                                   
- 响应时间 > 阈值 → 切换到更快模型                                        
                                                                          
手动切换：                                                                
                                                                          
```bash                                                                   
  # 切换当前会话模型                                                      
  /session model qwen3.5-plus                                             
  /session model qwen2.5-plus                                             
```                                                                       
                                                                          
```  
