from census import Census
from us import states
import pandas as pd
import numpy as np
import censusgeocode as cg
from time import sleep
import urllib.request
from urllib.parse import urlencode
import json
from sklearn.metrics import roc_auc_score, f1_score, confusion_matrix, accuracy_score


def getCensusCode(CLdata):
    #Adds census 'blockid' and 'GEOID10' columns to CL Data
    #CLdata must have columns called 'latitude' and 'longitude' as floats
    with pd.option_context('mode.chained_assignment', None):
        CLdata['blockid']=0
        for x in range(CLdata.shape[0]):
            row = CLdata.iloc[x]
            url = 'https://geocoding.geo.census.gov/geocoder/geographies/coordinates?'+urlencode({'x':str(row.longitude), 'y':str(row.latitude), 'benchmark':'4', 'vintage':'4', 'format':'json'})
            try:
                tmp = urllib.request.urlopen(url, timeout=60).read()
                CLdata.blockid.iloc[x] = json.loads(tmp)['result']['geographies']["2010 Census Blocks"][0]["GEOID"]
                print("First Try: ", x)
            except:
                try:
                    tmp = urllib.request.urlopen(url, timeout=60).read()
                    CLdata.blockid.iloc[x] = json.loads(tmp)['result']['geographies']["2010 Census Blocks"][0]["GEOID"]
                    print("Second Try: ", x)
                except:
                    CLdata.blockid.iloc[x] =  np.nan
                    print("Set to Nan: ", x)
    CLdata['GEOID10'] = CLdata.blockid.str.slice(0,11)
    return CLdata

def JoinNewData(old, new):
    #takes a newly collected set of CL data (with 'latitude' and 'longitude'
    #columns), adds 'date', 'blockid', and 'GEOID10' columns, then joins the
    #new collection to old
    x = old.append(getCensusCode(new))
    return x

def StateTractData(st):
    try:
        x = pd.read_csv(st+"tracts.csv",dtype = {'GEOID10':object,'blockid':object})
        print('read file')
    except:
        #Census API code
        c = Census("a36d29f80d1e867eb35fba5f935294928c1320be")
        statefips = eval("states."+st+".fips")
        x = pd.DataFrame(c.acs.get(['B02001_001E', 'B02001_002E','B02001_003E'], geo={'for': 'tract:*','in': 'state:{} county:*'.format(statefips)}))
        #construct column with tract code
        x['GEOID10']= x.state+x.county+x.tract
        #give it understandable columns, and created percent white column
        x.rename(columns={'B02001_001E': "total_pop", 'B02001_002E': 'white_pop','B02001_003E': 'black_pop'}, inplace=True)
        x['percent_white'] = x.white_pop/x.total_pop*100
        #Write to CSV
        x.to_csv(st+"tracts.csv")
        print('gened file')
    return x

def mergeCLandCensus(cldata,state,thresh=67):
    #merge with state tract data
    cl_withtracts = cldata.merge(StateTractData(state),how='left',on='GEOID10')
    #create a dummy variable '1' for neighborhoods with white population over a certain percentage
    cl_withtracts['high_white']=np.where(cl_withtracts['percent_white']>=thresh, 1, 0)
    return cl_withtracts

def prepforML(cldata,state='WA',thresh=67, x_cols = 'body_text', y_cols = 'high_white'):
    #we need a DF with one column called 'body_text' filled with CL
    #body text and one called 'GEOID10' that has 2010 census tract numbers
    # try clearing numeric characters and this specific phrase

    try:
        cldata.body_text = cldata.body_text.str.replace(r'\d','').str.replace('QR Code Link to This Post','')
        print('body_text cleaned')
    except:
        #if bodytext doesn't exist, return error
        return("body_text column needed")
    try:
        #try just returning the high_white and body_text columns

        df = cldata[[x_cols, y_cols]]
        print('just returning two columns')
    except:
        #if they're not there try merging with census data
        try:
            cldata = mergeCLandCensus(cldata,state,thresh)
            df = cldata[[x_cols, y_cols]]
            print('merged with census now returning two columns')
        except:
            #if that doesn't work, try getting census data
            try:
                print('getting census codes, this could take a while...')
                cldata = mergeCLandCensus(getCensusCode(cldata),state,thresh)
                df = cldata[[x_cols, y_cols]]
                print('got census info, merged with census, now returning two columns')
            except:
                return('no dice')
    return df.dropna()

#takes a pd.Series of Craigslist Neighborhood Names and returns a list of neighborhood names
def getNeighborhoodStopWords(rawhoods, city='seattle', merge=True, force_update=False):
    try:
        #if there's a file of stopwords for the city, just read it
        stopwords = pd.read_csv(city+"_stopwords.csv", merge=True)
    except:
        force_update=True
    if force_update==True:
        from nltk.tokenize import word_tokenize
        rawhoods = seattlefull.neighborhood
        stopwords = rawhoods.str.replace(r'\W',' ').str.replace(r'\d',' ').str.replace('WA','').str.lower().str.strip().dropna().unique()
        stopwords = list(set(word_tokenize(' '.join(stopwords))))
        if merge==True:
            from sklearn.feature_extraction import text
            stopwords = text.ENGLISH_STOP_WORDS.union(stopwords)
        pd.Series(list(stopwords)).to_csv(city+"stopwords.csv")
    return stopwords

#merge with sklearn default english stopwords list


#Import Ian's Seattle Data, clean it up and match to census tract
#import previous data
seattlefull =  pd.read_csv("seattlefull.csv", dtype = {'GEOID10':object,'blockid':object}).rename(columns={'body':'body_text'})
#import a new file
seattlenew = pd.read_csv('/Users/ikennedy/Documents/scrapypractice/rentalscrape/seattle1_15.csv').rename(columns={'body':'body_text'})
seattlenew['date'] = '1/15'
seattle = seattlenew
seattle = seattle.append(seattlenew)
seattle.shape
seattle.to_csv("8_12.csv")
seattlenew = getCensusCode(seattle)
seattlefull = seattlefull.append(seattlenew)
seattlefull.date.unique()
#append the new data
seattlefull.shape
#update the file
seattlefull.to_csv('seattlefull.csv')

seattlefull.head()
##Import CHess's set, rename column to 'body_text, make sure GEOID10 is type object'
hess_cl = pd.read_csv("/Users/ikennedy/OneDrive - UW/UW/Personal R/CL STUFF/Chris's Data/chcl.csv", dtype = {'GEOID10':object}).rename(columns={'listingText':'body_text'})

#clean and export only columns 'body_text' and 'highwhite'
hess_ml = prepforML(hess_cl)

#Repeat Above For Seattle sample, excluding date for validation
date = '12/31'
ian_ml = prepforML(seattlefull[seattlefull.date!=date])
df = hess_ml.append(ian_ml)

#repeat above for validation set using specific date
validation = prepforML(seattlefull[seattlefull.date==date])

'''prepare a train/test set and a validation set'''
# Split data into training and test sets
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(df['body_text'], df['high_white'], random_state=0)
S_X, x_0, S_y, y_0 = train_test_split(validation['body_text'], validation['high_white'], test_size = 0)
X_train.shape
S_X.shape
"""CountVectorizer"""
from sklearn.feature_extraction.text import CountVectorizer
# Fit the CountVectorizer to the training data
stop_words=getNeighborhoodStopWords(seattlefull,'seattle')
vect = CountVectorizer(stop_words=stop_words,ngram_range=(1,4)).fit(X_train)
len(vect.get_feature_names())
X_train_vectorized = vect.transform(X_train)
"""LogisticRegression"""
from sklearn.linear_model import LogisticRegression
model = LogisticRegression(C=.1).fit(X_train_vectorized, y_train)

# Predict the transformed test documents
predictions = model.predict_proba(vect.transform(X_test))[:,1]
sub_predictions = model.predict_proba(vect.transform(S_X))[:,1]
x['predictions'] = 0
x.predictions[x[0]>=0.45] = 1
x.predictions.mean()
print('AUC: ', roc_auc_score(y_test, predictions))
print('AUC: ', roc_auc_score(S_y, sub_predictions))
confusion_matrix(y_test, predictions)
confusion_matrix(S_y, sub_predictions)

accuracy_score(S_y, model.predict(vect.transform(S_X)))
f1_score(S_y, model.predict(vect.transform(S_X)))
# get the feature names as numpy array
feature_names = np.array(vect.get_feature_names())

# Sort the coefficients from the model
sorted_coef_index = model.coef_[0].argsort()

# Find the 10 smallest and 10 largest coefficients
# The 10 largest coefficients are being indexed using [:-11:-1]
# so the list returned is in order of largest to smallest
print('Smallest Coefs:\n{}\n'.format(feature_names[sorted_coef_index[:20]]))
print('Largest Coefs: \n{}'.format(feature_names[sorted_coef_index[-20:]]))





"""SVM"""
from sklearn.svm import SVC
svc = SVC(C=1000, probability = True).fit(X_train_vectorized,y_train)
predictions = svc.predict_proba(vect.transform(X_test))[:,1]
sub_predictions = svc.predict_proba(vect.transform(S_X))[:,1]
roc_auc_score(y_test, predictions)
roc_auc_score(S_y, sub_predictions)
accuracy_score(S_y, sub_predictions)

"""Random Forest Classifier"""
from sklearn.ensemble import RandomForestClassifier
rf = RandomForestClassifier().fit(X_train_vectorized,y_train)
predictions = rf.predict_proba(vect.transform(X_test))[:,1]
sub_predictions = rf.predict_proba(vect.transform(S_X))[:,1]
roc_auc_score(y_test, predictions)
roc_auc_score(S_y, sub_predictions)
accuracy_score(S_y, sub_predictions)

sorted_import_index = rf.feature_importances_.argsort()

print('Smallest Import:\n{}\n'.format(feature_names[sorted_import_index[:20]]))
print('Largest Import:\n{}\n'.format(feature_names[sorted_import_index[-400:]]))
feature_names.shape
features = feature_names[sorted_import_index[-1000:]]
'''LogisticRegression With Limited Features'''
lf_vect = CountVectorizer(stop_words=stop_words,ngram_range=(1,4), vocabulary = features).fit(X_train)
len(lf_vect.get_feature_names())
X_train_vectorized = lf_vect.transform(X_train)
X_train_vectorized
lf_model = LogisticRegression(C=.1).fit(X_train_vectorized, y_train)

predictions = lf_model.predict_proba(vect.transform(X_test))[:,1]
sub_predictions = lf_model.predict_proba(vect.transform(S_X))[:,1]

print('AUC: ', roc_auc_score(y_test, predictions))
print('AUC: ', roc_auc_score(S_y, sub_predictions))

feature_names = np.array(lf_vect.get_feature_names())

# Sort the coefficients from the model
sorted_coef_index = lf_model.coef_[0].argsort()

# Find the 10 smallest and 10 largest coefficients
# The 10 largest coefficients are being indexed using [:-11:-1]
# so the list returned is in order of largest to smallest
print('Smallest Coefs:\n{}\n'.format(feature_names[sorted_coef_index[:99]]))
print('Largest Coefs: \n{}'.format(feature_names[sorted_coef_index[-100:]]))

"""TfidfVectorizer"""

from sklearn.feature_extraction.text import TfidfVectorizer
tfidf = TfidfVectorizer(stop_words=stop_words, ngram_range =(1,2), vocabulary=features).fit(X_train)
tfidf
len(tfidf.get_feature_names())
X_train_tfidf = tfidf.transform(X_train)
model = LogisticRegression().fit(X_train_tfidf, y_train)
predictions = model.predict(tfidf.transform(X_test))
sub_predictions = model.predict(tfidf.transform(S_X))

print('AUC: ', roc_auc_score(y_test, predictions))
print('AUC: ', roc_auc_score(S_y, sub_predictions))


feature_names = np.array(tfidf.get_feature_names())

# Sort the coefficients from the model
sorted_coef_index = model.coef_[0].argsort()

# Find the 10 smallest and 10 largest coefficients
# The 10 largest coefficients are being indexed using [:-11:-1]
# so the list returned is in order of largest to smallest
print('Smallest Coefs:\n{}\n'.format(feature_names[sorted_coef_index[:20]]))
print('Largest Coefs: \n{}'.format(feature_names[sorted_coef_index[-50:]]))

svc = SVC(C=100).fit(X_train_tfidf,y_train)
predictions = svc.predict(tfidf.transform(X_test))
roc_auc_score(y_test, predictions)

"""With Cross Validation"""
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import make_pipeline
clf = make_pipeline(CountVectorizer(stop_words=stop_words,ngram_range=(1,4)), LogisticRegression(C=1))
score = cross_val_score(clf, X_train, y_train, cv=5, scoring = 'roc_auc')
score
fullmodel = LogisticRegression(C=.1).fit(vect.transform(df.listingText), df.high_white)
s_vectorized = vect.transform(S_X)
s_predictions = fullmodel.predict(s_vectorized)
roc_auc_score(S_y, s_predictions)
confusion_matrix(y_test, predictions)
confusion_matrix(S_y, s_predictions)

'''cluster'''
from sklearn.cluster import KMeans
hess_ml = prepforML(hess_cl,y_cols='percent_white')
date = '12/31'
ian_ml = prepforML(seattlefull[seattlefull.date!=date],y_cols='percent_white')
df = hess_ml.append(ian_ml)
#repeat above for validation set using specific date
validation = prepforML(seattlefull[seattlefull.date==date],y_cols='percent_white')

df.head()
