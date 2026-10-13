from io import BytesIO
import zipfile

import pytest
from maintenance.round12_recovery import single_native_archive, permanent
from benchmarks.round12_performance import fresh_request, stability
from scripts.round12_coverage import release_allowed
from src.fingerprint_pages import RequestPages


def archive(entries):
    out = BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        for name, raw in entries:
            z.writestr(name, raw)
    return out.getvalue()


def test_single_native_archive_rejects_traversal_extra_payload_and_fake_magic():
    pdf = b'%PDF-1.7\nfixture'
    assert single_native_archive(archive([('form.pdf', pdf)])) == (pdf, 'form.pdf')
    for entries in [[('../form.pdf', pdf)], [('form.pdf', pdf), ('run.exe', b'active')],
                    [('form.pdf', b'html')], [('form.doc', b'legacy')]]:
        with pytest.raises(ValueError):
            single_native_archive(archive(entries))


def test_permanent_failures_are_not_retried_as_transient():
    assert permanent(dict(final_reason='prior_permanent_or_policy_block_no_retry', previous_reason='timeout'))
    assert permanent(dict(final_reason='robots: percorso non consentito', previous_reason=''))
    assert not permanent(dict(final_reason='timeout', previous_reason='official_html_wrapper'))


def test_timed_requests_do_not_inherit_input_features_or_memo():
    context = RequestPages(('official public fixture text',), 'digital_pdf')
    context.queries()
    context.memo('private', lambda: 42)
    context.counters['page_renders'] = 2
    a, b = fresh_request(context), fresh_request(context)
    assert not a._queries and not a._memo and not a.counters and not a._visuals
    a.memo('private', lambda: 9)
    assert not b._memo and context._memo['private'] == 42


def test_stability_uses_median_run_p95_and_retains_fragile_runs():
    runs = lambda values: [dict(latency_ms=dict(p95=v)) for v in values]
    assert not stability(runs([100, 200, 251, 300, 350]))['required_pass']
    result = stability(runs([100, 150, 240, 300, 350]))
    assert result['required_pass'] and result['median_p95'] == 240
    assert not result['preferred_stability_pass'] and result['prudent_fragile']
    assert not stability(runs([100, 120]))['required_pass']


def test_failed_coverage_prevents_unknown_release_execution():
    assert not release_allowed(dict(file_backed_percent=84.9, all_operational_percent=90))
    assert not release_allowed(dict(file_backed_percent=85, all_operational_percent=69.9))
    assert release_allowed(dict(file_backed_percent=85, all_operational_percent=70))
