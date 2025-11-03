# packages
library(dplyr)
library(tidyr)
library(forcats)
library(ggplot2)
library(janitor)

### Set path to the latest EHS data
setwd("~/Policy/Data")
EHS_path <- "./EHS/EHS_data_files/"


#### Read latest EHS data ####

physical_20_21 <- read.table(paste0(EHS_path,"physical_20_plus_21_eul.tab"), header = TRUE, sep = "\t") %>% 
  select(serialanon,
         dwtype8x, alltypex, dwage4x,
  )


EHS <- physical_20_21 %>%
   mutate(
    # set factor levels
    dwtype = factor(dwtype8x, levels = c(1:8), labels = c("small terraced house","medium/large terraced house","semi-detached house",
                                                                        "detached house","bungalow","converted flat",
                                                                        "purpose built flat, low rise", "purpose built flat, high rise")),
    dwtype_simple = fct_collapse(dwtype, flat = c("purpose built flat, low rise", "purpose built flat, high rise", "converted flat"), 
                                     terraced_bungalow_semi = c("small terraced house","medium/large terraced house","semi-detached house", "bungalow"),
                                     detached =  c("detached house")),
# This is the key step - dwage4x is the age variable - it can be found and checked in the documentation 
    dw_type_age = factor(case_when(
      dwtype_simple == "flat" & dwage4x %in% c(1,2) ~ "flat pre-1945",
      dwtype_simple == "flat" & dwage4x %in% c(3,4) ~ "flat post-1945",
      dwtype == "bungalow" & dwage4x %in% c(1,2) ~ "bungalow pre-1945",
      dwtype == "bungalow" & dwage4x %in% c(3,4) ~ "bungalow post-1945",
      dwtype8x <4 & dwage4x %in% c(1,2) ~ "semi-detached and terraced house pre-1945",
      dwtype8x <4 & dwage4x %in% c(3,4) ~ "semi-detached and terraced house post-1945",
      dwtype == "detached house" & dwage4x %in% c(1,2) ~ "detached house pre-1945",
      dwtype == "detached house" & dwage4x %in% c(3,4) ~ "detached house post-1945",
      TRUE ~ "error"
    )),
     ),
  )


### Total matrices and export EHS ####

# edit this as needed

EHS_long_total <- EHS %>%
  # GROUP BY WHATEVER YOU NEED : group_by(.....) %>%
# This is important - each row needs to be multiplied by weighted_count, that's the weight 
  summarise(weighted_count = sum(weight_hh), .groups = 'drop') %>%
  ungroup()

 

# export
# edit as needed

write.csv(EHS_long_total, "./EHS/EHS_long_2021.csv", row.names = FALSE)
