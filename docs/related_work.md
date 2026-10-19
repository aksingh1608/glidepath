# Related work

This review covers five groups of work: point prediction of landing time, interval prediction of landing time, conformal prediction, A-CDM, and Trajectory-Based Operations. A short section on data and tools follows. Keys in brackets match `references.bib`. We checked every source against the link given. On 2026-10-19 we checked the remaining open points against the sources named in each entry. Where we could not verify a detail, we say so.

Sources from the seed list that we left out:

* ICAO A-CDM milestone and performance metric templates. We found the official reference. They are Attachment 4.8 (A-CDM milestone procedure template) and Attachment 5.2 (A-CDM Performance Metrics Template) of the AFI A-CDM Implementation Guide, first edition, 14 July 2025, published by the ICAO WACAF and ESAF Regional Offices [icao2025afiacdm]. The guide is regional guidance for Africa, and it calls its templates drafts. We still cite the EUROCONTROL manual as our main A-CDM source, because Frankfurt follows the European process.

Sources we found and chose not to include, to keep the list short: Meinshausen 2006 (quantile regression forests), Xu and Xie 2021 (EnbPI), the FAA TBO Industry Day deck, and Vella, Gauci and Dingli 2025 (holding time prediction at Heathrow from OpenSky data, JOAS, doi:10.59490/joas.2024.7890). The last one may be worth adding if H4 needs more context.

## 1. Point prediction of ETA or landing time

### Wang, Liang and Delahaye 2020 [wang2020automated]
Z. Wang, M. Liang, D. Delahaye. Automated data-driven prediction on aircraft Estimated Time of Arrival. *Journal of Air Transport Management* 88, 101840, 2020. https://doi.org/10.1016/j.jairtraman.2020.101840

* **What it does.** The authors build a pipeline that cleans ADS-B tracks and predicts the time from terminal area entry to the runway. They train separate candidate models for each runway configuration and find that a stacked ensemble works best.
* **Data and airport.** ADS-B data from the Beijing terminal manoeuvring area, with nested cross validation.
* **Measures.** Point error of the ETA (MAE and RMSE).
* **How we differ.** We predict along the whole approach rather than at one entry point, and we attach a calibrated interval to each prediction.

### Silvestre et al. 2021 [silvestre2021deep]
J. Silvestre, M. de Santiago, A. Bregon, M. A. Martínez-Prieto, P. C. Álvarez-Esteban. On the Use of Deep Neural Networks to Improve Flights Estimated Time of Arrival Predictions. *Engineering Proceedings* 13(1), 3, 2021 (9th OpenSky Symposium). https://doi.org/10.3390/engproc2021013003

* **What it does.** The authors compare several LSTM models that take a sequence of past flight states and predict arrival time. They find that the length of the input sequence matters more than the choice of architecture.
* **Data and airport.** OpenSky Network ADS-B data for flights that arrived at Madrid Barajas-Adolfo Suárez (LEMD) from 8 to 28 January 2020. The authors chose this period to avoid the Spanish Christmas holidays and the effects of COVID-19.
* **Measures.** MAE and RMSE, also at fixed times before the end of the flight.
* **How we differ.** We use the same open data source, but we ask when the prediction becomes reliable, not how small the average error is.

### Dhief et al. 2020 [dhief2020predicting]
I. Dhief, Z. Wang, M. Liang, S. Alam, M. Schultz, D. Delahaye. Predicting Aircraft Landing Time in Extended-TMA Using Machine Learning Methods. ICRAT 2020. https://hal-enac.archives-ouvertes.fr/hal-02907597

* **What it does.** The authors study which features drive landing time in an extended terminal area and compare three machine learning algorithms, of which Extra-Trees does best. Traffic demand and density, surface wind, position and time of day carry the most signal.
* **Data and airport.** Surveillance data within a 100 NM extended TMA around Singapore Changi.
* **Measures.** RMSE of landing time.
* **How we differ.** They show that traffic density affects point accuracy. Our H3 asks whether it also delays the trust point.

### Wells et al. 2023 [wells2023prediction]
J. Z. Wells, T. G. Puranik, K. M. Kalyanam, M. Kumar. Prediction of Aircraft Estimated Time of Arrival Using a Supervised Learning Approach. *IFAC-PapersOnLine* 56(3), 43 to 48, 2023 (3rd Modeling, Estimation and Control Conference). https://doi.org/10.1016/j.ifacol.2023.11.008 (open copy: https://ntrs.nasa.gov/citations/20230010340)

* **What it does.** The authors fuse track, weather and flight plan data and train a random forest to predict remaining flight time. The prediction is made once, when the aircraft is about 200 miles out.
* **Data and airport.** Arrivals at Dallas/Fort Worth.
* **Measures.** MAE and the share of flights predicted within a fixed tolerance of five minutes.
* **How we differ.** They report a hit rate at one fixed distance. We track every later prediction of a flight and require the whole run of intervals to stay inside the window.

### Huang et al. 2025 [huang2025efficient]
L. Huang, Y. Zhang, Y. Yin, S. Zhang, Y. Zhang. Efficient Real-Time Aircraft ETA Prediction via Feature Tokenization Transformer. arXiv:2508.09144, 2025. https://arxiv.org/abs/2508.09144

* **What it does.** The authors feed raw state features into a Transformer through a feature tokenizer, which reduces hand-crafted feature work. They report better accuracy than XGBoost at lower compute cost, with predictions updated every second.
* **Data and airport.** One month of ADS-B data for arrivals between 10 and 300 NM from Singapore Changi. The label is time to runway threshold.
* **Measures.** Point error and inference time.
* **How we differ.** Their model gives no interval. We need intervals to define the trust point.

### DFS Aviation Services, Arrival Manager [dfsas_aman]
DFS Aviation Services. Arrival Manager (AMAN): High-performance system for optimal operational decisions. Product flyer, February 2020. https://dfs-as.aero/download/12107

* **What it does.** AMAN is an operational controller tool that computes an approach sequence and target landing times from speed, route, weather and aircraft performance. DFS reports long operational use and a planning horizon of up to 200 NM.
* **Data and airport.** Radar and flight plan data at the deploying unit. The flyer lists Frankfurt Airport first under references and customers. It does not say which DFS unit runs the system for Frankfurt, and we found no open DFS source that states this.
* **Measures.** The product sheet gives no accuracy figures.
* **How we differ.** AMAN plans the sequence that controllers then impose. We only observe the outcome from open data, and we measure how early that outcome can be trusted.

### FlightAware Foresight [flightaware_foresight] and the Fraport deployment [flightaware2019fraport]
FlightAware. FlightAware Foresight, product page. https://flightaware.com/commercial/foresight
FlightAware and Fraport AG. Fraport to Deploy FlightAware Predictive Technology at Frankfurt Airport. Press release, July 2019. https://flightaware.com/news/article/Fraport-to-Deploy-FlightAware-Predictive-Technology-at-Frankfurt-Airport/423

* **What it does.** Foresight is a commercial machine learning service that predicts landing time and gate arrival time from live positions, airport conditions, weather and metadata. In 2019 Fraport agreed to use FlightAware landing time estimates at Frankfurt to plan airfield operations and ground staff.
* **Data and airport.** Global FlightAware data. The press release covers Frankfurt.
* **Measures.** No public accuracy figures. The press release does not use the name Foresight, so we cite the two sources apart.
* **How we differ.** The Frankfurt operator already buys landing time estimates for ground staff planning. This shows the need. We study the same use case with open data and an explicit trust criterion that anyone can check.

## 2. Probabilistic or interval prediction of landing time

### Glina, Jordan and Ishutkina 2012 [glina2012tree]
Y. Glina, R. Jordan, M. Ishutkina. A Tree-Based Ensemble Method for the Prediction and Uncertainty Quantification of Aircraft Landing Times. 10th Conference on Artificial and Computational Intelligence, AMS Annual Meeting, 2012. https://ams.confex.com/ams/92Annual/webprogram/Paper201872.html

* **What it does.** The authors use quantile regression forests to predict time to wheels on and a 90 percent interval for each flight. They show that interval width shrinks as the aircraft gets closer to the runway.
* **Data and airport.** ASDI tracks, ASDE-X surface data and ASPM throughput data for Dallas/Fort Worth over five days. Samples are taken at fixed distances from the airport, and the train and test split is random by case, not by day.
* **Measures.** MAE by distance and the spread of interval widths. We found no check of empirical interval coverage in the paper.
* **How we differ.** This is the closest earlier work. We add a coverage check per distance band, a conformal correction, a split by day, and the trust point, which joins width and correctness over time.

### Tielrooij et al. 2015 [tielrooij2015predicting]
M. Tielrooij, C. Borst, M. M. van Paassen, M. Mulder. Predicting arrival time uncertainty from actual flight information. 11th USA/Europe ATM R&D Seminar, 2015. https://research.tudelft.nl/en/publications/predicting-arrival-time-uncertainty-from-actual-flight-information(8c67690d-21ee-4461-8d41-83ebf9f8a4ef).html

* **What it does.** The authors argue that arrival time errors will never vanish, so an arrival manager should know how large the error is likely to be. They predict that uncertainty from the past accuracy of current arrival estimates.
* **Data and airport.** We could not open the paper itself. Chapter 3 of Tielrooij's 2022 TU Delft dissertation states that it is based on this paper [tielrooij2022arrival]. There the data are the Flight Update Messages from the EUROCONTROL Network Manager for inbound flights to Amsterdam Airport Schiphol, for all of 2013 and 2014. The reference time is the reported landing time.
* **Measures.** In the dissertation chapter, ETA errors are grouped by flight status, time of day and prediction horizon, and a Johnson distribution is fitted to each group. Fit is checked with the Kolmogorov-Smirnov statistic, using bootstrap samples and held-out points from the same group. The chapter also reports the width of the central 95 percent of each distribution by horizon. The paper may differ in detail from the dissertation chapter.
* **How we differ.** They estimate the size of the error. We ask from which moment the error stays inside a window the ground team can use.

### Förster and Fricke 2024 [forster2024probabilistic]
S. Förster, H. Fricke. Probabilistic Prediction of Estimated Time of Arrival: Identifying Sources of Variance and Out-of-Sample Issues. ICRAT 2024. https://fis.tu-dresden.de/portal/files/50632989/forster_2024_probabilistic_prediction_of_estimated_time_of_arrival_-_identifying_sources_of.pdf

* **What it does.** The authors compare three neural approaches to ETA uncertainty with an earlier quantile regression forest. A mixture density network does best on CRPS. They then show that on out-of-sample traffic the intervals cover far less often than claimed.
* **Data and airport.** NASA Sherlock data for the Phoenix TRACON and Phoenix Sky Harbor.
* **Measures.** CRPS and prediction interval coverage probability (PICP).
* **How we differ.** Their undercoverage result motivates our H1. We test a conformal fix per distance band and measure the effect on the trust point.

### Kim, Yoon and Lee 2025 [kim2025probabilistic]
K. Kim, S. Yoon, K. Lee. Probabilistic Multi-Agent Aircraft Landing Time Prediction. arXiv:2512.08281, 2025, version 3. https://arxiv.org/abs/2512.08281

* **What it does.** The authors predict a Gaussian landing time distribution for several aircraft at once, with attention between nearby aircraft to capture controller vectoring. Version 3 reruns all experiments after a data leakage fix, so only version 3 numbers should be cited.
* **Data and airport.** A year of ADS-B arrivals at Incheon from a 70 NM boundary, split by time.
* **Measures.** MAE, RMSE, MAPE and rank agreement of the arrival order. The paper shows uncertainty only in figures and reports no coverage or calibration check.
* **How we differ.** They model traffic interaction to improve the point estimate. We test whether the stated interval is honest and how early it becomes usable.

## 3. Conformal prediction

### Romano, Patterson and Candès 2019 [romano2019conformalized]
Y. Romano, E. Patterson, E. Candès. Conformalized Quantile Regression. NeurIPS 2019, pp. 3543 to 3553. https://proceedings.neurips.cc/paper_files/paper/2019/file/5103c3584b063c431bd1268e9b5e76fb-Paper.pdf

* **What it does.** The method fits lower and upper quantile models, then widens or narrows both by one amount learned on a held-out calibration set. This keeps the input-dependent width of quantile regression and adds a finite-sample coverage guarantee under exchangeability.
* **Data.** Standard regression benchmarks, not aviation.
* **Measures.** Coverage and mean interval length.
* **How we differ.** This is our calibration step. We apply it per distance band and test whether the guarantee survives a change of day, where exchangeability may not hold.

### Angelopoulos and Bates 2023 [angelopoulos2023conformal]
A. N. Angelopoulos, S. Bates. Conformal Prediction: A Gentle Introduction. *Foundations and Trends in Machine Learning* 16(4), 494 to 591, 2023. https://doi.org/10.1561/2200000101 (preprint arXiv:2107.07511)

* **What it does.** A practical tutorial on split conformal prediction, conformalized quantile regression, conditional coverage checks, and extensions for distribution shift. It includes code.
* **Data.** Worked examples from several fields.
* **Measures.** Not an empirical study.
* **How we differ.** We use it as the reference for our coverage definitions and for the checks of coverage within groups, such as distance bands.

### Gibbs and Candès 2021 [gibbs2021adaptive]
I. Gibbs, E. Candès. Adaptive Conformal Inference Under Distribution Shift. NeurIPS 2021. https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html

* **What it does.** The method updates one parameter of the conformal threshold online after each observed error. It reaches the target coverage over long runs even when the data distribution drifts.
* **Data.** Two real-world time series, not aviation.
* **Measures.** Long-run coverage frequency.
* **How we differ.** We use plain split conformal calibration on one calibration day. This paper is the natural next step if test day coverage fails, and we cite it under threats to validity.

### Sadeek, Hanaoka and Sugishita 2026 [sadeek2026uncertainty]
S. N. Sadeek, S. Hanaoka, K. Sugishita. Uncertainty quantification of departure delay considering network properties and conformal prediction framework. *Journal of Air Transport Management* 136, 103037, 2026. https://doi.org/10.1016/j.jairtraman.2026.103037

* **What it does.** The authors predict average departure delay at Japanese hub airports with network features and compare several conformal methods. All methods struggle to keep coverage when delays shift fast, as in the COVID period.
* **Data and airport.** Japanese domestic flights from 2018 to 2021.
* **Measures.** Interval coverage and responsiveness at several uncertainty levels.
* **How we differ.** They apply conformal prediction to airport-level delay. We apply it to the landing time of single flights on approach.

## 4. A-CDM and the role of ELDT

### EUROCONTROL Airport CDM Implementation Manual [eurocontrol2017acdm]
EUROCONTROL. Airport CDM Implementation: The Manual. Edition 5.0, March 2017. https://www.eurocontrol.int/sites/default/files/publication/files/airport-cdm-manual-2017.PDF

* **What it does.** The manual defines the A-CDM milestones and the times shared between airport partners, including the estimated landing time (ELDT). At the local radar milestone it calls ELDT accuracy important because stand, gate and handling decisions are taken then, and it advises against stand or gate changes after ELDT minus 30 minutes. At the final approach milestone, usually a few minutes before landing, handlers start to move marshals and ground equipment.
* **Data and airport.** Guidance for all European A-CDM airports. Frankfurt is an A-CDM airport. EUROCONTROL lists Frankfurt among the airports where A-CDM is fully implemented [eurocontrol_acdm_page]. Fraport states that it started the project with DFS in April 2008 and that A-CDM entered regular operations at Frankfurt in February 2011 [fraport_acdm].
* **Measures.** Annex 1 lists two ELDT indicators: ELDT against actual landing time (accuracy) and ELDT against time (timeliness).
* **How we differ.** The manual names both accuracy and timeliness but does not join them into one number. Our trust lead joins them per flight: how long before touchdown the estimate is both narrow and correct.

## 5. Trajectory-Based Operations

### ICAO 2018, AN-Conf/13-WP/52 [icao2018tbo]
ICAO, Thirteenth Air Navigation Conference. Support for a Global Trajectory-Based Operations (TBO) Framework. Working Paper AN-Conf/13-WP/52, presented by the United States, 2018. https://www.icao.int/sites/default/files/Meetings/2018/AN-CONF-13/Documentation/WP/wp_052_en.pdf

* **What it does.** The paper restates the ICAO definition of TBO: managing four-dimensional trajectories in a consistent way by sharing and maintaining trajectory information. It lists better predictability as one aim and describes the FAA move from distance-based to time-based management.
* **Data.** Policy paper, no data.
* **Measures.** Not an empirical study.
* **How we differ.** TBO assumes that trajectory times can be predicted and shared. We measure how early one of those times, touchdown, can be trusted at Frankfurt from open data.

### SESAR, Trajectory Based Operations [sesar_tbo]
SESAR Joint Undertaking. TBOP: Trajectory Based Operations. European ATM Master Plan portal. https://atmmasterplan.eu/eoc-flagships/2475718

* **What it does.** SESAR describes TBO as an umbrella concept made of many solutions. Each flight gets an agreed reference trajectory that the airspace user commits to fly and that air navigation service providers and airports commit to support.
* **Data.** Concept page, no data.
* **Measures.** Not an empirical study.
* **How we differ.** In a full TBO system the reference trajectory would carry a landing time. Until then, ground teams must infer it from surveillance data, which is what we study.

## 6. Data and tools

### Schäfer et al. 2014 [schafer2014bringing]
M. Schäfer, M. Strohmeier, V. Lenders, I. Martinovic, M. Wilhelm. Bringing Up OpenSky: A Large-scale ADS-B Sensor Network for Research. IPSN 2014, pp. 83 to 94. https://doi.org/10.1109/IPSN.2014.6846743

* **What it does.** The paper describes the OpenSky Network: low-cost ADS-B receivers run by volunteers feed a central database that researchers can query.
* **Data.** The early network over Central Europe.
* **Measures.** Coverage and message volume of the network.
* **How we differ.** This is our data source. Its volunteer coverage is the first threat to validity in our plan.

### Olive 2019 [olive2019traffic]
X. Olive. traffic, a toolbox for processing and analysing air traffic data. *Journal of Open Source Software* 4(39), 1518, 2019. https://doi.org/10.21105/joss.01518

* **What it does.** A Python library to download, clean, resample and analyse trajectories from OpenSky and other sources.
* **Data.** Not applicable.
* **Measures.** Not applicable.
* **How we differ.** We checked the code. The current pipeline does not use traffic. It calls the OpenSky REST API directly and processes the data with pandas. We cite traffic as an open tool for the same task.

## Gap statement

Earlier work predicts landing time well from surveillance data [wang2020automated, silvestre2021deep, dhief2020predicting, wells2023prediction, huang2025efficient]. Some work also gives an interval for each flight [glina2012tree, forster2024probabilistic, kim2025probabilistic]. Two facts stand out. First, most of the interval studies we reviewed report no empirical coverage check, and the one that does finds severe undercoverage on unfamiliar traffic [forster2024probabilistic]. Second, these studies report accuracy at fixed distances or fixed times before landing. None of them asks from what moment the interval for one flight stays both narrow and correct.

The A-CDM manual names ELDT accuracy and ELDT timeliness as separate indicators [eurocontrol2017acdm]. Tielrooij et al. predict the size of arrival time errors for arrival managers [tielrooij2015predicting]. Wells et al. count flights within a five minute tolerance at one distance [wells2023prediction]. These are the closest ideas to our trust point that we found. None of them requires every later interval to stay inside the window.

We found no peer-reviewed study of landing time prediction at Frankfurt, although Fraport uses commercial estimates there [flightaware2019fraport]. We also found no study that applies conformal calibration to landing time. The conformal studies in aviation we found address departure delay [sadeek2026uncertainty] and aggregate inbound demand [simons2026probabilistic], not the landing time of single flights.

Glidepath is therefore a focused study. It applies a known calibration method [romano2019conformalized] to Frankfurt arrivals from open ADS-B data [schafer2014bringing]. It measures a per-flight trust lead that joins the accuracy and timeliness ideas of A-CDM. Our search was broad but not exhaustive. We do not claim that the trust point is new. We claim only that we did not find it in the sources above. On 2026-10-19 we ran further web searches for conformal prediction of landing time and for landing time papers at the SESAR Innovation Days. They added only the LVNL demand thesis [simons2026probabilistic]. We could not query Google Scholar directly, so a final Scholar search is still worth doing before submission.
