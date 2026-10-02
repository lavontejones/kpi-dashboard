import unittest
import pandas as pd
from src.kpis import compute_kpis
class KpiTests(unittest.TestCase):
    def setUp(self):
        self.jobs=pd.DataFrame({'date':pd.to_datetime(['2026-01-01','2026-01-02']), 'revenue':[100.,200.], 'cogs':[60.,120.]})
        self.exp=pd.DataFrame({'date':pd.to_datetime(['2026-01-02']), 'amount':[20.]})
        self.cash=pd.DataFrame({'week_start':pd.to_datetime(['2026-01-02','2026-01-01']), 'balance':[500.,400.]})
        self.pipe=pd.DataFrame({'stage':['Lead','Won','Lost'], 'value':[50.,70.,20.], 'age_days':[1,10,3]})
    def calc(self, mult=1):
        return compute_kpis(self.jobs,self.exp,self.cash,self.pipe,pd.Timestamp('2026-01-02'),pd.Timestamp('2026-01-02'),mult)
    def test_known_values_and_prior(self):
        k=self.calc()
        self.assertEqual(k['revenue'], {'value':200.,'prior':100.})
        self.assertAlmostEqual(k['gross_margin_pct']['value'],.4)
        self.assertEqual(k['net_cash_flow']['value'],60.)
        self.assertEqual(k['cash_balance']['value'],500.)
        self.assertAlmostEqual(k['cash_runway_weeks']['value'],500/980)
        self.assertEqual(k['active_pipeline_value']['value'],50.)
        self.assertEqual(k['win_rate']['value'],.5)
    def test_scenario_operating_leverage(self):
        self.assertAlmostEqual(self.calc(.85)['net_cash_flow']['value'],44.4)
    def test_empty_period_and_no_prior(self):
        k=compute_kpis(self.jobs.iloc[:0],self.exp.iloc[:0],self.cash.iloc[:0],self.pipe.iloc[:0],pd.Timestamp('2020-01-01'),pd.Timestamp('2020-01-02'))
        self.assertEqual(k['revenue'],{'value':0.,'prior':None})
        self.assertEqual(k['win_rate']['value'],0.)
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError): self.calc(0)
        with self.assertRaises(ValueError): compute_kpis(self.jobs,self.exp,self.cash,self.pipe,pd.Timestamp('2026-01-02'),pd.Timestamp('2026-01-01'))
if __name__=='__main__': unittest.main()
