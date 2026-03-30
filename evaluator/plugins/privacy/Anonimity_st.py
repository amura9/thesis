from sklearn.metrics import accuracy_score
import pandas as pd

class AnonymitySetSize:
    hidden = True #do not find it

    def __init__(self):
        
        self.name = "Anonymity Set Size for Sensitive Features"
        self.needs_sensitive = True
        self.needs_conditional_variable = False  # Non serve una variabile condizionale per questa metrica

    def calculate_anonymity_set_size_for_sensitive_features(self, sensitive_features):
        # Conteggio delle combinazioni uniche delle feature sensibili
        combination_counts = sensitive_features.value_counts()

        # Calcolo della dimensione media dell'anonymity set
        average_anonymity_set_size = combination_counts.mean()

        return combination_counts, average_anonymity_set_size

    def evaluate(self, y_true, y_pred, X, sensitive_features, conditional_variable=None): #which signals are needed for execution y_true, 
        #model prediction: y_pred, X = test set
        results = {}

        # Calcoliamo la dimensione del set di anonimizzazione per ogni combinazione di feature sensibili
        try:
            combination_counts, average_anonymity_set_size = self.calculate_anonymity_set_size_for_sensitive_features(sensitive_features)

            # Convertiamo combination_counts in un DataFrame per una visualizzazione completa
            combination_counts_df = combination_counts.reset_index()
            combination_counts_df.columns = list(sensitive_features.columns) + ['count']

            # Struttura i risultati
            results["Anonymity Set Sizes"] = combination_counts_df
            results["Average Anonymity Set Size"] = average_anonymity_set_size

        except Exception as e:
            results["error"] = str(e)

        return resultset #standard result