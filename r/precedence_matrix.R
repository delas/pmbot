args <- commandArgs(TRUE)
log <- args[1]
pic <- args[2]

library(bupaR)

data <- read_xes(log)
dc <- data %>% precedence_matrix(type = "absolute") %>% plot

png(filename=pic)
plot(dc)
dev.off()
