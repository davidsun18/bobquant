```markdown                                                               
  # ROUTING.md - Boss Bot 任务分发路由表                                  
                                                                          
  ## 🎯 任务识别与分发规则                                                
                                                                          
  ### 关键词匹配规则                                                      
                                                                          
  | 关键词 | 目标 Agent | 优先级 | 示例 |                                 
  |--------|-----------|--------|- -----|                                 
  | 数据采集 | Data Bot | 高 | "采集昨日行情" |                           
  | 获取行情 | Data Bot | 高 | "获取沪深 300 成分股数据" |                
  | 获取财务 | Data Bot | 高 | "获取财报数据" |                           
  | 策略研发 | Quant Research Bot | 高 | "研发新策略" |                   
  | 因子挖掘 | Quant Research Bot | 高 | "挖掘动量因子" |                 
  | 回测 | Quant Research Bot | 高 | "回测策略表现" |                     
  | 开发 | Dev Bot | 中 | "开发新模块" |                                  
  | 代码 | Dev Bot | 中 | "编写交易接口" |                                
  | 系统 | Dev Bot | 中 | "优化系统性能" |                                
  | 优化 | Dev Bot | 中 | "优化延迟" |                                    
  | 执行 | Execution Bot | 高 | "执行调仓指令" |                          
  | 下单 | Execution Bot | 高 | "下单买入" |                              
  | 持仓 | Execution Bot | 高 | "查询持仓" |                              
  | 交易 | Execution Bot | 高 | "今日交易计划" |                          
  | 合规 | Compliance Bot | 高 | "合规检查" |                             
  | 监管 | Compliance Bot | 高 | "监管报告" |                             
  | 限制检查 | Compliance Bot | 高 | "检查持仓限制" |                     
  | 报告 | Report Bot | 中 | "生成绩效报告" |                             
  | 汇总 | Report Bot | 中 | "汇总本周数据" |                             
  | 绩效 | Report Bot | 中 | "绩效归因分析" |                             
                                                                          
  ## 🔄 分发流程                                                          
                                                                          
```                                                                       
                                                                          
用户指令                                                                  
   ↓                                                                      
Boss Bot 接收                                                             
   ↓                                                                      
关键词匹配                                                                
   ↓                                                                      
识别目标 Agent                                                            
   ↓                                                                      
分发任务                                                                  
   ↓                                                                      
等待结果                                                                  
   ↓                                                                      
汇总输出                                                                  
                                                                          
```                                                                       
                                                                          
  ## ⚡ 优先级规则                                                        
                                                                          
  - **高优先级** - 交易相关、风控相关，立即处理                           
  - **中优先级** - 研发、开发相关，队列处理                               
  - **低优先级** - 报告、汇总相关，定时处理                               
                                                                          
  ## 🚨 异常处理                                                          
                                                                          
  - 无法识别任务类型 → 询问用户澄清                                       
  - 目标 Agent 不可用 → 通知用户并记录                                    
  - 任务超时 → 主动询问进度                                               
```    
