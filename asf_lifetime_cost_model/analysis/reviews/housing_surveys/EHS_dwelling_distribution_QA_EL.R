## ---------------------------
##
## This script checks the code from EHS_SHCS_process_v12.R that processes
## the EHS files to recreate a table that groups dwellings by recoded variables:
## - dw_type_age
## - tenure
## - poverty_AHC
## - gas
## - loft_insul_125
## - hhsizex
## - weighted_count
##
## The table to be recreated is in the Cost_model_final_updated_June25 spreadsheet
## tab "EHS20192020" and tab "EHS_sum".
## Original code has been re-ordered or modified to try and recreate this table.
##
## ---------------------------

## set working directory
setwd("/home/eglucas/Projects/quality_assurance_local/housing_stock_analysis_mk") 

## ---------------------------

## load packages
library(dplyr)
library(forcats)

## ---------------------------

## set file paths
EHS_path <- "./data/EHS/"

## ---------------------------

## read EHS files with only select fields

# Dataset with general information on weightings, tenure, vacancy and region
general_20_21 <- read.table(paste0(EHS_path,"general20_plus_21_eul.tab"), header = TRUE, sep = "\t") %>% 
  select(serialanon, 
         weight_hh = aagph2021, # EL: rounded household weight for 2-year paired sample
         # weight_hh = aagpd2021, # EL: rounded dwelling weight for 2 year physical survey sample
         tenure4x)

# Dataset on household information from householder interviews 
interviews_20_21 <- read.table(paste0(EHS_path,"interview_20_plus_21_eul.tab"), header = TRUE, sep = "\t") %>% 
  select(serialanon,
         hhsizex, # EL: added this for number of persons in household
         tenure4,
         AHCinceqv60h, # after housing costs below 60% of median income (weighted by peoplegross)
  )

# Dataset on physical dwelling information from physica surveys
physical_20_21 <- read.table(paste0(EHS_path,"physical_20_plus_21_eul.tab"), header = TRUE, sep = "\t") %>% 
  select(serialanon,
         dwtype8x,
         dwage4x,
         mainsgas, # 0: off, 1: on
         loftinsx, # loft insulation thickness
  )

# Dataset with fuel poverty variables derived from EHS
fuel_poverty_20_21 <- read.table(paste0(EHS_path,"fuel_poverty_2021_ukda_eul.tab"), header = TRUE, sep = "\t") %>%
  select(serialanon,
         aagph2021, # EL: household weight
         fpLILEEflg # EL: fuel poverty flag - Low Income Low Energy Efficiency Measure
  )

## ---------------------------

## Combining and processing all EHS datasets

EHS <- interviews_20_21 %>%
  # join all EHS datasets by EHS case number serialanon
  inner_join(physical_20_21, by = "serialanon") %>%
  inner_join(general_20_21, by = "serialanon") %>% 
  inner_join(fuel_poverty_20_21, by = "serialanon") %>%
  
  # recode variables for readability
  mutate(
    # dwelling type and age
    dw_age = factor(dwage4x, levels = c(1:4), labels = c("pre-1919", "1919–1944", "1945–1964","post-1964")),
    dwtype = factor(dwtype8x, levels = c(1:8), labels = c("small terraced house","medium/large terraced house","semi-detached house",
                                                          "detached house","bungalow","converted flat",
                                                          "purpose built flat, low rise", "purpose built flat, high rise")),
    dwtype_simple = fct_collapse(dwtype, flat = c("purpose built flat, low rise", "purpose built flat, high rise", "converted flat"), 
                                 terraced_bungalow_semi = c("small terraced house","medium/large terraced house","semi-detached house", "bungalow"),
                                 detached =  c("detached house")),
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
    # tenure
    tenure4x = factor(tenure4x, levels = c(1:4), labels = c("owner occupied", "private rented", "local authority", "housing association")),
    tenure = fct_collapse(tenure4x, social = c("local authority", "housing association")),
    # fuel poverty after housing costs
    poverty_ahc = factor(AHCinceqv60h, levels = c(0,1), labels = c("Not in poverty", "In poverty")),
    # mains gas
    gas = factor(mainsgas, levels = c(1, 0), labels = c("on gas grid", "off gas grid")),
    # loft insulation
    loft_insul125 = factor(case_when(
      loftinsx %in% c(0:124) ~ "Loft uninsulated", # less than 125mm insulation or none
      loftinsx >=125 ~ "Loft insulated", # 125+
      loftinsx == -9 ~ "N/A"
    )),
  ) %>%
  
  # keep only relevant columns
  select(serialanon, hhsizex, weight_hh, dw_type_age, tenure, poverty_ahc, gas, loft_insul125)

## ---------------------------

## Group by specified columns

EHS_20_21_full_table_check <- EHS %>%
  group_by(dw_type_age, tenure, poverty_ahc, gas, loft_insul125, hhsizex) %>%
  summarise(weighted_count = sum(weight_hh), .groups = 'drop') %>%
  ungroup()

EHS_20_21_dwelling_distribution_total <- EHS_20_21_full_table_check %>%
  group_by(dw_type_age) %>%
  summarise(total_weighted_count = sum(weighted_count), .groups = 'drop')%>%
  ungroup()


## ---------------------------

## Save to .csv

write.csv(EHS_20_21_full_table_check, "./outputs/EHS_20_21_full_table_check.csv", row.names = FALSE)
write.csv(EHS_20_21_dwelling_distribution_total, "./outputs/EHS_20_21_dwelling_distribution_total.csv", row.names = FALSE)