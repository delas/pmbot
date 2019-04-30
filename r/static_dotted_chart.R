args <- commandArgs(TRUE)
log <- args[1]
pic <- args[2]

library(bupaR)

data <- read_xes(log)
dc <- data %>% dotted_chart(x = "absolute", y = "start")
png(filename=pic)
plot(dc)
dev.off()
