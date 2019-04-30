args <- commandArgs(TRUE)
log <- args[1]
pic <- args[2]

library(bupaR)

data <- read_xes(log)
dc <- data %>% dotted_chart(x = "relative", y = "duration")
png(filename=pic)
plot(dc)
dev.off()
