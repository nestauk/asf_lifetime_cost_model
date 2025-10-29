# packages
library(dplyr)
library(tidyr)
library(forcats)
library(ggplot2)
library(janitor)


# setwd("~/Policy/Data") ## <- here you might need to set the working directory

EHS_path <- "./raw_data/"
SHCS_path <- "./raw_data/shcs2021_dataset.tab"

# EHS_path <- "./EHS/EHS_data_files/"
# SHCS_path <- "./SHCS/tab/shcs2021_dataset.tab"
# WHCS_path <- "./WHCS/tab/physical_whcs17.tab"
### Function to scale to total no. of homes (for Scotland)

scale_nation <- function(df, nation) {
  total_hh_England <- 23868877
  total_hh_Scotland <- 2529000
  total_hh_Wales <- 1347100
  if (nation == "England") {
    scaling_factor <- total_hh_England / nrow(EHS)
  } else if (nation=="Scotland") {
    scaling_factor <- total_hh_Scotland / nrow(SHCS)
  } else {
    scaling_factor <- total_hh_Wales / nrow(WHCS)
}
  cols_to_scale <- sapply(df, is.numeric)
  scaled_df <- df %>%
    mutate(across(which(cols_to_scale), ~ round(.x * scaling_factor, 0)))
  return(scaled_df)
}

#### Read latest EHS data ####
general_20_21 <- read.table(paste0(EHS_path,"general20_plus_21_eul.tab"), header = TRUE, sep = "\t") %>%
  select(serialanon,
         weight_hh = aagph2021,
         tenure4x)
interviews_20_21 <- read.table(paste0(EHS_path,"interview_20_plus_21_eul.tab"), header = TRUE, sep = "\t") %>%
  select(serialanon,
         tenure4, tenex,
  )
physical_20_21 <- read.table(paste0(EHS_path,"physical_20_plus_21_eul.tab"), header = TRUE, sep = "\t") %>%
  select(serialanon,
         EPC_full = EPceeb12e,
         fuelx # main fuel type
  )

# 21 fuel poverty data ####
fuel_poverty_20_21 <- read.table(paste0(EHS_path,"fuel_poverty_2021_ukda_eul.tab"), header = TRUE, sep = "\t") %>%
  select(serialanon, aagph2021, fpLILEEflg)


#### Combine latest EHS data frames ####

EHS <- interviews_20_21 %>%
  inner_join(physical_20_21, by = "serialanon") %>%
  inner_join(general_20_21, by = "serialanon") %>%
  inner_join(fuel_poverty_20_21, by = "serialanon") %>%
  mutate(
    # set factor levels
    EPC = factor(EPC_full, levels = c(2:7), labels = c("A/B", "C", "D", "E", "F", "G")) %>% fct_collapse(.,"F/G" = c("F", "G")),
    tenure4x = factor(tenure4x, levels = c(1:4), labels = c("owner occupied", "private rented", "local authority", "housing association")),
    tenure = fct_collapse(tenure4x, social = c("local authority", "housing association")),
  )

#### Read and transform SHCS data ####

SHCS <- read.table(SHCS_path, header = TRUE, sep = "\t") %>%
  select(tenure5x = outten_5, #tenure
         EPC_full = EPC2012_v9.93, #EPC (AB and FG merged)
         FP_status = FP3mis9010_rrrstidis_full, # fuel poverty status
  ) %>%
  mutate(
    EPC = factor(EPC_full) %>% recode("AB" = "A/B", "FG" = "F/G") %>% factor(., levels = c("A/B","C", "D","E","F/G")),
    fuel_poverty = factor(case_when(FP_status == 1 ~ "Fuel poor",
                                 TRUE ~ "Not fuel poor")),
    tenure5x = factor(tenure5x, levels = c(1:5), labels = c("owned outright", "mortgaged", "LA", "HA", "private rented")),
    tenure = fct_collapse(tenure5x, "owner occupied" = c("owned outright", "mortgaged"), "social" = c("LA", "HA"))
    )

#### Total matrices and export ####

EHS_long_total <- EHS %>%
  group_by(tenure, fuel_poverty) %>%
  # multiply data by weight (which is in the dataset)
  summarise(weighted_count = sum(weight_hh), .groups = 'drop') %>%
  ungroup()

EHS_wide_total <- EHS_long_total %>%
# Spread the EPC ratings into columns
  pivot_wider(names_from = EPC, values_from = weighted_count, values_fill = list(weighted_count = 0)) %>%
  mutate(nation = "England") %>% relocate(nation, .before = 1)

SHCS_wide_total <- SHCS %>%
  group_by(tenure, fuel_poverty, EPC) %>%
  summarise(count = n(), .groups = 'drop') %>%
  ungroup() %>%
# Spread the EPC ratings into columns
  pivot_wider(names_from = EPC, values_from = count, values_fill = list(count = 0)) %>%
  # scale to the number of households in Scotland (afaik the SCHS does not include a weighting variable)
  scale_nation("Scotland") %>%
  mutate(nation = "Scotland") %>% relocate(nation, .before = 1)

# export - these tables are then copied into the Data_misc google sheet
write.csv(EHS_wide_total, "./EHS/EHS_matrix_2021.csv", row.names = FALSE)
write.csv(SHCS_wide_total, "./SHCS/SHCS_matrix_2021.csv", row.names = FALSE)
