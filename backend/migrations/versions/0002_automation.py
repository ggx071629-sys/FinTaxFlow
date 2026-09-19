"""Frozen additive E2 schema; preserves all original records."""
from alembic import op
import sqlalchemy as sa
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("demo_settings", sa.Column("declaration_fault", sa.String(32), nullable=False, server_default="NONE"))
    op.execute('\nCREATE TABLE automation_tasks (\n\tnumber VARCHAR(40) NOT NULL, \n\tkind VARCHAR(24) NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tperiod VARCHAR(7), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tevents JSONB NOT NULL, \n\tfailure_reason VARCHAR(500), \n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (number), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE extension_files (\n\tname VARCHAR(255) NOT NULL, \n\tmedia_type VARCHAR(80) NOT NULL, \n\tcontent BYTEA, \n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE declarations (\n\ttask_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tfiling_id UUID NOT NULL, \n\tperiod VARCHAR(7) NOT NULL, \n\ttax_type VARCHAR(16) NOT NULL, \n\tbusiness_number VARCHAR(40) NOT NULL, \n\tsales_amount VARCHAR(32) NOT NULL, \n\ttax_amount VARCHAR(32) NOT NULL, \n\tfault VARCHAR(32) NOT NULL, \n\tacceptance_number VARCHAR(40), \n\taccepted_at TIMESTAMP WITH TIME ZONE, \n\tsubmission_count INTEGER NOT NULL, \n\treceipt_file_id UUID, \n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (company_id, generation, period, tax_type), \n\tUNIQUE (task_id), \n\tFOREIGN KEY(task_id) REFERENCES automation_tasks (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tUNIQUE (filing_id), \n\tFOREIGN KEY(filing_id) REFERENCES tax_filings (id), \n\tUNIQUE (business_number), \n\tUNIQUE (acceptance_number), \n\tFOREIGN KEY(receipt_file_id) REFERENCES extension_files (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE imports (\n\tkind VARCHAR(16) NOT NULL, \n\tperiod VARCHAR(7), \n\tfile_name VARCHAR(255) NOT NULL, \n\tsource_file_id UUID NOT NULL, \n\tissue_file_id UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(source_file_id) REFERENCES extension_files (id), \n\tFOREIGN KEY(issue_file_id) REFERENCES extension_files (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE billing_batches (\n\timport_id UUID NOT NULL, \n\ttask_id UUID NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (import_id), \n\tFOREIGN KEY(import_id) REFERENCES imports (id), \n\tUNIQUE (task_id), \n\tFOREIGN KEY(task_id) REFERENCES automation_tasks (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE import_lines (\n\timport_id UUID NOT NULL, \n\trow_number INTEGER NOT NULL, \n\tbusiness_number VARCHAR(200) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\traw_fields JSONB NOT NULL, \n\tfields JSONB NOT NULL, \n\tissues JSONB NOT NULL, \n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (import_id, row_number), \n\tFOREIGN KEY(import_id) REFERENCES imports (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE reconciliations (\n\ttask_id UUID NOT NULL, \n\tbank_import_id UUID NOT NULL, \n\tledger_import_id UUID NOT NULL, \n\tresults JSONB NOT NULL, \n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (bank_import_id, ledger_import_id), \n\tUNIQUE (task_id), \n\tFOREIGN KEY(task_id) REFERENCES automation_tasks (id), \n\tFOREIGN KEY(bank_import_id) REFERENCES imports (id), \n\tFOREIGN KEY(ledger_import_id) REFERENCES imports (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE batch_lines (\n\tbatch_id UUID NOT NULL, \n\timport_line_id UUID NOT NULL, \n\tbusiness_number VARCHAR(200) NOT NULL, \n\tid UUID NOT NULL, \n\tcompany_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (company_id, generation, business_number), \n\tFOREIGN KEY(batch_id) REFERENCES billing_batches (id), \n\tUNIQUE (import_line_id), \n\tFOREIGN KEY(import_line_id) REFERENCES import_lines (id), \n\tFOREIGN KEY(company_id) REFERENCES companies (id)\n)\n\n')
    op.execute('\nCREATE TABLE batch_attempts (\n\tbilling_task_id UUID NOT NULL, \n\tline_id UUID NOT NULL, \n\tposition INTEGER NOT NULL, \n\tPRIMARY KEY (billing_task_id), \n\tUNIQUE (line_id, position), \n\tFOREIGN KEY(billing_task_id) REFERENCES billing_tasks (id), \n\tFOREIGN KEY(line_id) REFERENCES batch_lines (id)\n)\n\n')
    op.execute('CREATE INDEX ix_automation_tasks_company_id ON automation_tasks (company_id)')
    op.execute('CREATE INDEX ix_automation_tasks_kind ON automation_tasks (kind)')
    op.execute('CREATE INDEX ix_automation_tasks_status ON automation_tasks (status)')
    op.execute('CREATE INDEX ix_extension_files_company_id ON extension_files (company_id)')
    op.execute('CREATE INDEX ix_declarations_company_id ON declarations (company_id)')
    op.execute('CREATE INDEX ix_imports_company_id ON imports (company_id)')
    op.execute('CREATE INDEX ix_billing_batches_company_id ON billing_batches (company_id)')
    op.execute('CREATE INDEX ix_import_lines_company_id ON import_lines (company_id)')
    op.execute('CREATE INDEX ix_import_lines_import_id ON import_lines (import_id)')
    op.execute('CREATE INDEX ix_reconciliations_company_id ON reconciliations (company_id)')
    op.execute('CREATE INDEX ix_batch_lines_batch_id ON batch_lines (batch_id)')
    op.execute('CREATE INDEX ix_batch_lines_company_id ON batch_lines (company_id)')
    op.execute('CREATE INDEX ix_batch_attempts_line_id ON batch_attempts (line_id)')

def downgrade():
    op.drop_table('batch_attempts')
    op.drop_table('batch_lines')
    op.drop_table('reconciliations')
    op.drop_table('import_lines')
    op.drop_table('billing_batches')
    op.drop_table('imports')
    op.drop_table('declarations')
    op.drop_table('extension_files')
    op.drop_table('automation_tasks')
    op.drop_column("demo_settings", "declaration_fault")
