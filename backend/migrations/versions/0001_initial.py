"""Frozen original schema; E2 additions belong to 0002."""
from alembic import op
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('\nCREATE TABLE companies (\n\tid UUID NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\ttax_id VARCHAR(18) NOT NULL, \n\tservice_status VARCHAR(80) NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tseed_key VARCHAR(40) NOT NULL, \n\tPRIMARY KEY (id)\n)\n\n')
    op.execute('\nCREATE TABLE users (\n\tid UUID NOT NULL, \n\tusername VARCHAR(80) NOT NULL, \n\tpassword_hash VARCHAR(128) NOT NULL, \n\tname VARCHAR(80) NOT NULL, \n\tPRIMARY KEY (id)\n)\n\n')
    op.execute('\nCREATE TABLE accounting_summaries (\n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tperiod VARCHAR(7) NOT NULL, \n\tincome NUMERIC(14, 2) NOT NULL, \n\texpense NUMERIC(14, 2) NOT NULL, \n\tprofit NUMERIC(14, 2) NOT NULL, \n\treceivable NUMERIC(14, 2) NOT NULL, \n\tpayable NUMERIC(14, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (company_id, period), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE activities (\n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\ttitle VARCHAR(200) NOT NULL, \n\ttime TIMESTAMP WITH TIME ZONE NOT NULL, \n\tobject_type VARCHAR(16) NOT NULL, \n\tobject_id VARCHAR(64) NOT NULL, \n\tperiod VARCHAR(7), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE billing_tasks (\n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tnumber VARCHAR(32) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tinput_snapshot JSONB NOT NULL, \n\tnet_amount NUMERIC(14, 2) NOT NULL, \n\ttax_amount NUMERIC(14, 2) NOT NULL, \n\ttotal_amount NUMERIC(14, 2) NOT NULL, \n\ttax_rate VARCHAR(8) NOT NULL, \n\tseller_name VARCHAR(200) NOT NULL, \n\tseller_tax_id VARCHAR(18) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tfailure_reason TEXT, \n\tinvoice_id UUID, \n\tinvoice_number VARCHAR(32), \n\tsource_task_id UUID, \n\tbound_result VARCHAR(16) NOT NULL, \n\tprocessing_started_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tUNIQUE (number), \n\tFOREIGN KEY(company_id) REFERENCES companies (id), \n\tFOREIGN KEY(source_task_id) REFERENCES billing_tasks (id)\n)\n\n')
    op.execute('\nCREATE TABLE demo_settings (\n\tuser_id UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tnext_result VARCHAR(16) NOT NULL, \n\tPRIMARY KEY (user_id, company_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE idempotency_keys (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\toperation VARCHAR(40) NOT NULL, \n\tkey VARCHAR(120) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tobject_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (user_id, company_id, operation, key), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE reset_runs (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tmessage TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE tax_filings (\n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tname VARCHAR(80) NOT NULL, \n\tperiod VARCHAR(7) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tfailure_reason TEXT, \n\tnodes JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (company_id, period, name), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE user_companies (\n\tuser_id UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tPRIMARY KEY (user_id, company_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE billing_events (\n\tid UUID NOT NULL, \n\ttask_id UUID NOT NULL, \n\tlabel VARCHAR(80) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\ttime TIMESTAMP WITH TIME ZONE, \n\tnote TEXT, \n\tsort INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(task_id) REFERENCES billing_tasks (id)\n)\n\n')
    op.execute('\nCREATE TABLE invoices (\n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tnumber VARCHAR(32) NOT NULL, \n\tinvoice_type VARCHAR(32) NOT NULL, \n\tdirection VARCHAR(16) NOT NULL, \n\tissued_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tbuyer_name VARCHAR(200) NOT NULL, \n\tbuyer_tax_id VARCHAR(18) NOT NULL, \n\tseller_name VARCHAR(200) NOT NULL, \n\tseller_tax_id VARCHAR(18) NOT NULL, \n\titem_name VARCHAR(200) NOT NULL, \n\tnet_amount NUMERIC(14, 2) NOT NULL, \n\ttax_amount NUMERIC(14, 2) NOT NULL, \n\ttotal_amount NUMERIC(14, 2) NOT NULL, \n\ttax_rate VARCHAR(8) NOT NULL, \n\tverification_status VARCHAR(16) NOT NULL, \n\tverification_note TEXT NOT NULL, \n\tpdf_path VARCHAR(500), \n\tpdf_available BOOLEAN NOT NULL, \n\tsource_task_id UUID, \n\tPRIMARY KEY (id), \n\tUNIQUE (number), \n\tUNIQUE (source_task_id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id), \n\tFOREIGN KEY(source_task_id) REFERENCES billing_tasks (id)\n)\n\n')
    op.execute('CREATE UNIQUE INDEX ix_users_username ON users (username)')
    op.execute('CREATE INDEX ix_accounting_summaries_company_id ON accounting_summaries (company_id)')
    op.execute('CREATE INDEX ix_accounting_summaries_period ON accounting_summaries (period)')
    op.execute('CREATE INDEX ix_activities_company_id ON activities (company_id)')
    op.execute('CREATE INDEX ix_activities_time ON activities (time)')
    op.execute('CREATE INDEX ix_billing_tasks_company_id ON billing_tasks (company_id)')
    op.execute('CREATE INDEX ix_billing_tasks_created_at ON billing_tasks (created_at)')
    op.execute('CREATE INDEX ix_billing_tasks_status ON billing_tasks (status)')
    op.execute('CREATE INDEX ix_reset_runs_company_id ON reset_runs (company_id)')
    op.execute('CREATE INDEX ix_reset_runs_status ON reset_runs (status)')
    op.execute('CREATE INDEX ix_reset_runs_user_id ON reset_runs (user_id)')
    op.execute('CREATE INDEX ix_tax_filings_company_id ON tax_filings (company_id)')
    op.execute('CREATE INDEX ix_tax_filings_period ON tax_filings (period)')
    op.execute('CREATE INDEX ix_billing_events_task_id ON billing_events (task_id)')
    op.execute('CREATE INDEX ix_invoices_issued_at ON invoices (issued_at)')
    op.execute('CREATE INDEX ix_invoices_company_id ON invoices (company_id)')
    op.execute('CREATE INDEX ix_invoices_verification_status ON invoices (verification_status)')
    op.execute('CREATE INDEX ix_invoices_direction ON invoices (direction)')

def downgrade():
    op.drop_table('invoices')
    op.drop_table('billing_events')
    op.drop_table('user_companies')
    op.drop_table('tax_filings')
    op.drop_table('reset_runs')
    op.drop_table('idempotency_keys')
    op.drop_table('demo_settings')
    op.drop_table('billing_tasks')
    op.drop_table('activities')
    op.drop_table('accounting_summaries')
    op.drop_table('users')
    op.drop_table('companies')
