args <- commandArgs(TRUE)
log <- args[1]
pic <- args[2]

library(bupaR)

data <- read_xes(log)
dc <- data %>% resource_frequency("resource") %>% plot
png(filename=pic)
plot(dc)
dev.off()
