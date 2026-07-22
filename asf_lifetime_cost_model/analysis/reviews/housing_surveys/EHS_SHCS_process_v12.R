# packages
library(dplyr)
library(tidyr)
library(forcats)
library(ggplot2)
library(janitor)


setwd("~/Policy/Data")
# setwd("/Users/martina/Documents/Nesta")
EHS_path <- "./EHS/EHS_data_files/"
SHCS_path <- "./SHCS/tab/shcs2021_dataset.tab"
WHCS_path <- "./WHCS/tab/physical_whcs17.tab"

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
         # AHCinceq, # after housing costs equivalised weekly income
         AHCinceqv60h,# poverty line
         BHCinceqv60h, # poverty line
         hhltsick, # disability or long-term illness
         hhvulx # means-tested disability benefits
  )
physical_20_21 <- read.table(paste0(EHS_path,"physical_20_plus_21_eul.tab"), header = TRUE, sep = "\t") %>%
  select(serialanon,
         dwtype8x, alltypex, dwage4x,
         EPC_full = EPceeb12e,
         mainsgas, # 0: off, 1: on
         loftu4,
         loftins4,loftinsx, # loft insulation with imputed thickness
         wins95x, # cavity wall insulation
         wallinsz, # cavity/solid wall insulation
         fuelx # main fuel type
  )

# 21 data ####
fuel_poverty_20_21 <- read.table(paste0(EHS_path,"fuel_poverty_2021_ukda_eul.tab"), header = TRUE, sep = "\t") %>%
  select(serialanon, aagph2021, fpLILEEflg)


#### Combine latest EHS data frames ####

EHS <- interviews_20_21 %>%
  inner_join(physical_20_21, by = "serialanon") %>%
  inner_join(general_20_21, by = "serialanon") %>%
  inner_join(fuel_poverty_20_21, by = "serialanon") %>%
  mutate(
    # set factor levels
    illness_disability = factor(hhltsick, levels = c(1, 2, -8), labels = c("Yes", "No", "NA")), # 36.7 %
    vulnerable = factor(hhvulx, levels = c(1, 2), labels = c("Vulnerable", "Not vulnerable")), # 26.3 % - benefits
    dw_age = factor(dwage4x, levels = c(1:4), labels = c("pre-1919", "1919–1944", "1945–1964","post-1964")),
    EPC = factor(EPC_full, levels = c(2:7), labels = c("A/B", "C", "D", "E", "F", "G")) %>% fct_collapse(.,"F/G" = c("F", "G")),
    dwtype = factor(dwtype8x, levels = c(1:8), labels = c("small terraced house","medium/large terraced house","semi-detached house",
                                                                        "detached house","bungalow","converted flat",
                                                                        "purpose built flat, low rise", "purpose built flat, high rise")),
    dwtype_simple = fct_collapse(dwtype, flat = c("purpose built flat, low rise", "purpose built flat, high rise", "converted flat"),
                                     terraced_bungalow_semi = c("small terraced house","medium/large terraced house","semi-detached house", "bungalow"),
                                     detached =  c("detached house")),
    house_flat = fct_collapse(dwtype_simple, "house" = c("detached", "terraced_bungalow_semi")),
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
    tenure4x = factor(tenure4x, levels = c(1:4), labels = c("owner occupied", "private rented", "local authority", "housing association")),
    mortgage = factor(case_when(tenex == 1 ~ "owns with mortgage", tenex == 2 ~ "owns outright", TRUE ~ "not owner occupied")),
    wall_insul = factor(wallinsz, levels = c(1:5), labels = c("cavity with insulation", "cavity uninsulated", "solid with insulation",
                                                              "solid uninsulated", "other")
    ),
    loft_insul100 = factor(case_when(
      loftins4 %in% c(1,2) ~ "Loft uninsulated", # less than 100mm insulation or none
      loftins4 >=3 ~ "Loft insulated", # 100+
      loftins4 == -9 ~ "N/A"
    )),
    loft_insul125 = factor(case_when(
      loftinsx %in% c(0:124) ~ "Loft uninsulated", # less than 125mm insulation or none
      loftinsx >=125 ~ "Loft insulated", # 125+
      loftinsx == -9 ~ "N/A"
    )),
    loft_insul150 = factor(case_when(
      loftins4 %in% c(1,2) ~ "Loft uninsulated", # less than 150mm insulation or none
      loftins4 >3 ~ "Loft insulated", # 100+
      loftins4 == -9 ~ "N/A"
    )),
    CW_insul = factor(case_when(
      wins95x %in% c(1,2) ~ "CW insulated",
      wins95x == 3 ~ "CW uninsulated",
      TRUE ~ "N/A"
    )),
    SW_insul = factor(case_when(
      wall_insul == "solid with insulation" ~ "SW insulated",
      wall_insul == "solid uninsulated" ~ "SW uninsulated",
      TRUE ~ "N/A"
    )),
    tenure = fct_collapse(tenure4x, social = c("local authority", "housing association")),
    gas = factor(mainsgas, levels = c(1, 0), labels = c("on gas grid", "off gas grid")),
    fuel = factor(fuelx, levels = c(1:4, -8), labels = c("gas/LPG", "oil", "solid", "electrical", "communal")),
    poverty_BHC = factor(BHCinceqv60h, levels = c(0,1), labels = c("Not in poverty", "In poverty")),
    poverty_AHC = factor(AHCinceqv60h, levels = c(0,1), labels = c("Not in poverty", "In poverty")),
    fuel_poverty = factor(fpLILEEflg, levels = c(0,1), labels = c("Not fuel poor", "Fuel poor")),
  ) %>%
  select(-alltypex, -hhltsick, -BHCinceqv60h, -hhvulx, -mainsgas, -loftu4,-loftins4,-loftinsx,-wins95x, -wallinsz, -fuelx)




## EHS tests ##
  #
  # tabyl(EHS, dwtype_simple, dwage4x) %>% adorn_totals("col") %>% adorn_totals("row")
  # tabyl(EHS, dwtype8x, dwage4x) %>% adorn_totals("col") %>% adorn_totals("row")



#### Read and transform SHCS data ####

SHCS <- read.table(SHCS_path, header = TRUE, sep = "\t") %>%
  select(tenure5x = outten_5, #tenure
         typdwell, # type of dwelling
         EPC_full = EPC2012_v9.93, #EPC (AB and FG merged)
         incomeAHC = incAHC_Stage3, # annual income AHC of the whole household
         FP_status = FP3mis9010_rrrstidis_full, # fuel poverty status
         gas = sgngrid_new, # gas grid (0: on, 1: off)
         primFuel_biomass, # main fuel type
         loftins_newTS, # loft insulation
         insulateWalls, # CW insulation
         health, # Any long-term sick/disabled in household # 50.1 %
         disab_benefits = totaldlapipaa, # disability benefits numeric - 15.4% > 0
  ) %>%
  mutate(
    EPC = factor(EPC_full) %>% recode("AB" = "A/B", "FG" = "F/G") %>% factor(., levels = c("A/B","C", "D","E","F/G")),
    fuel_poverty = factor(case_when(FP_status == 1 ~ "Fuel poor",
                                 TRUE ~ "Not fuel poor")),
    tenure5x = factor(tenure5x, levels = c(1:5), labels = c("owned outright", "mortgaged", "LA", "HA", "private rented")),
    tenure = fct_collapse(tenure5x, "owner occupied" = c("owned outright", "mortgaged"), "social" = c("LA", "HA")),
    mortgage = factor(case_when(tenure5x == "mortgaged" ~ "owns with mortgage",
                                tenure5x == "owned outright" ~ "owns outright",
                                TRUE ~ "not owner occupied")),
    typdwell = factor(typdwell, levels = c(1:7), labels = c("detached", "semi","terrace", "tenement", "4-in-a-block", "tower/slab", "converted flat")),
    dwtype_simple = fct_collapse(typdwell, flat = c("converted flat", "tenement", "4-in-a-block"),
                          terraced_bungalow_semi = c("semi","terrace"),
                          detached =  c("detached", "tower/slab")),
    house_flat = fct_collapse(dwtype_simple, "house" = c("detached", "terraced_bungalow_semi")),
    gas = factor(gas, levels = c(0, 1), labels = c("on gas grid", "off gas grid")),
    loft_insul100 = factor(case_when(
      loftins_newTS <= 4 ~ "Loft uninsulated", # less than 100mm insulation
      loftins_newTS %in% c(5:12) ~ "Loft insulated", # 100+
      loftins_newTS >=13 ~ "N/A"
    )),
    loft_insul150 = factor(case_when(
      loftins_newTS <= 5 ~ "Loft uninsulated", # less than 150mm insulation
      loftins_newTS %in% c(6:12) ~ "Loft insulated", # 150+
      loftins_newTS >=13 ~ "N/A"
    )),
    wall_insul = factor(case_when(
      insulateWalls %in% c(2:4) ~ "cavity with insulation",
      insulateWalls <2 ~ "cavity uninsulated",
      insulateWalls %in% c(6,7) ~ "solid with insulation",
      insulateWalls %in% c(5, 5.5) ~ "solid uninsulated"
    )),
    # CW_insul = factor(case_when(
    #   insulateWalls %in% c(2:4) ~ "CW insulated",
    #   insulateWalls < 2 ~ "CW uninsulated",
    #   insulateWalls > 4 ~ "N/A"
    # )),
    # 0 = CW not technically viable - moved to CW N/A from C/W uninsulted
    CW_insul = factor(case_when(
      insulateWalls %in% c(2:4) ~ "CW insulated",
      insulateWalls == 1 ~ "CW uninsulated",
      insulateWalls > 4 | insulateWalls == 0 ~ "N/A" # solid wall, or CW insulation not viable
    )),
    SW_insul = factor(case_when(
      wall_insul == "solid with insulation" ~ "SW insulated",
      wall_insul == "solid uninsulated" ~ "SW uninsulated",
      TRUE ~ "N/A"
    )),
    fuel = factor(case_when(
      primFuel_biomass %in% c(1,3) ~ "gas/LPG", primFuel_biomass == 2 ~ "electrical", primFuel_biomass == 4 ~ "oil",
      primFuel_biomass %in% c(5:6) ~ "solid", primFuel_biomass >= 7 ~ "communal"
    )),
    vulnerable = factor(case_when(disab_benefits>0 ~ "Vulnerable", TRUE ~ "Not vulnerable"))
  ) %>%
  select(-FP_status, -loftins_newTS)


## Check Scottish data
#
tabyl(SHCS, fuel_poverty, fuel) %>% adorn_totals("row") %>% adorn_pct_formatting()
# tabyl(SHCS, mortgage, tenure) %>% adorn_totals("row")


#### Read and transform WHCS data ####

WHCS <- read.table(WHCS_path, header = TRUE, sep = "\t") %>%
  select(
    # tenure5x = outten_5, #tenure
         dwtype7x, # type of dwelling
         EPCeeb = EPCeeb12e, #EPC (ABC merged)
     # incomeAHC = incAHC_Stage3, # annual income AHC of the whole household
     # FP_status = FP3mis9010_rrrstidis_full, # fuel poverty status
         fuelx, # main fuel type
         wallinsz, # wall insulation
  ) %>%
  mutate(
    EPC = factor(EPCeeb, levels = c(1:5), labels = c("A/B/C", "D", "E", "F", "G")) %>% fct_collapse(.,"F/G" = c("F", "G")),
    dwtype7x = factor(dwtype7x, levels = c(1:7), labels = c("end terrace", "mid terrace", "semi-detached", "detached",
                                                            "purpose built flat", "converted flat",  "flat plus non residential")),
    house_flat = fct_collapse(dwtype7x, "house" = c("end terrace", "mid terrace", "semi-detached", "detached"),
                              "flat" = c("purpose built flat", "converted flat",  "flat plus non residential")),
    wall_insul = factor(wallinsz, levels = c(1:5), labels = c("cavity with insulation", "cavity uninsulated", "solid with insulation",
                                                              "solid uninsulated", "other")),
    SW_insul = factor(case_when(
      wall_insul == "solid with insulation" ~ "SW insulated",
      wall_insul == "solid uninsulated" ~ "SW uninsulated",
      TRUE ~ "N/A"
    )),
    CW_insul = factor(case_when(
      wall_insul == "cavity with insulation" ~ "CW insulated",
      wall_insul == "cavity uninsulated" ~ "CW uninsulated",
      TRUE ~ "N/A"
    )),
    fuel = factor(fuelx, levels = c(1:4, -8), labels = c("gas/LPG", "oil", "solid", "electrical", "communal")),
  )



#### Total matrices and export ####

EHS_long_total <- EHS %>%
  group_by(tenure, fuel_poverty, fuel) %>%
  summarise(weighted_count = sum(weight_hh), .groups = 'drop') %>%
  ungroup()

EHS_wide_total <- EHS_long_total %>%
# Spread the EPC ratings into columns
  pivot_wider(names_from = EPC, values_from = weighted_count, values_fill = list(weighted_count = 0)) %>%
  mutate(nation = "England") %>% relocate(nation, .before = 1)


SHCS_long_total <- SHCS %>%
  group_by(tenure, fuel_poverty, fuel) %>%
  summarise(count = n(), .groups = 'drop') %>%
  ungroup() %>%
  scale_nation("Scotland") %>%
  mutate(nation = "Scotland") %>% relocate(nation, .before = 1)

SHCS_wide_total <- SHCS %>%
  group_by(tenure, fuel_poverty, fuel, EPC) %>%
  summarise(count = n(), .groups = 'drop') %>%
  ungroup() %>%
# Spread the EPC ratings into columns
  pivot_wider(names_from = EPC, values_from = count, values_fill = list(count = 0)) %>%
  scale_nation("Scotland") %>%
  mutate(nation = "Scotland") %>% relocate(nation, .before = 1)

WHCS_long_total <- WHCS %>%
  group_by(fuel) %>%
  summarise(count = n(), .groups = 'drop') %>%
  ungroup() %>%
  scale_nation("Wales") %>%
  mutate(nation = "Wales") %>% relocate(nation, .before = 1)

WHCS_wide_total <- WHCS %>%
  group_by(fuel, house_flat, CW_insul, SW_insul, EPC) %>%
  summarise(count = n(), .groups = 'drop') %>%
  ungroup() %>%
  # Spread the EPC ratings into columns
  pivot_wider(names_from = EPC, values_from = count, values_fill = list(count = 0)) %>%
  scale_nation("Wales") %>%
  mutate(nation = "Wales") %>% relocate(nation, .before = 1)


# export
write.csv(EHS_wide_total, "./EHS/EHS_matrix_2021.csv", row.names = FALSE)
write.csv(SHCS_wide_total, "./SHCS/SHCS_matrix_2021.csv", row.names = FALSE)

write.csv(EHS_long_total, "./EHS/EHS_long_2021.csv", row.names = FALSE)
write.csv(SHCS_long_total, "./SHCS/SHCS_long_2021.csv", row.names = FALSE)
write.csv(WHCS_long_total, "./WHCS/WHCS_long_2021.csv", row.names = FALSE)


write.csv(WHCS_wide_total, "./WHCS/WHCS_matrix.csv", row.names = FALSE)


SHCS_FP_fuel <- SHCS %>%
  group_by(fuel_poverty, fuel, gas) %>%
  summarise(count = n(), .groups = 'drop') %>%
  ungroup() %>%
  # pivot_wider(names_from = wall_insul, values_from = count, values_fill = list(count = 0)) %>%
  scale_nation("Scotland")
