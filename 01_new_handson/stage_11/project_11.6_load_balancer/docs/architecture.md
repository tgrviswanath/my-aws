# Architecture Notes — Project 11.6

## ALB vs NLB vs CLB
| | ALB | NLB | CLB |
|--|--|--|--|
| Layer | 7 (HTTP) | 4 (TCP/UDP) | 4+7 |
| Routing | Path, host, headers | IP+port | Basic |
| Use case | Web apps, microservices | Low latency, TCP | Legacy |
| WebSocket | Yes | Yes | Limited |
| Static IP | No (use NLB) | Yes | No |

## Health Check Flow
```
ALB → GET /health every 30s → EC2
  200 OK → healthy (after 2 consecutive)
  non-200 or timeout → unhealthy (after 2 consecutive)
  unhealthy → removed from rotation
  healthy again → added back automatically
```
