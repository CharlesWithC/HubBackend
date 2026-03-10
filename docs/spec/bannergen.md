# Banner Generator

This is a technical documentation on the evolution of `bannergen`.

For practical usage, see [/docs/bannergen.md](/docs/bannergen.md).

## The History

`bannergen` was initially very resource-intensive, which led to certain design decisions that stuck despite later optimizations on both `main` and `bannergen`, because the decisions didn't have practical downsides.

The first version of `bannergen` lived inside `main` as a regular API route, before `main` received proper multi-tenancy support (see [/docs/spec/multihub.md](/docs/spec/multihub.md) for more information). This implies that heavy libraries such as `pillow` and `numpy` are loaded each time `main` launches, consuming significant RAM resources. Also, this version was very CPU-intensive due to using 3400x600 sized banners and lack of optimizations, which made performance unstable especially when there is a spike of `/member/banner` requests.

This led to the decision of separating `bannergen` into a separate server instance, as an independent banner generator that receives all banner parameters through POST request (rather than config file) from `main` program. This reduced RAM usage significantly as heavy libraries are only loaded once.

However, due to lack of optimization, `bannergen` still often caused CPU spikes and deadlocks which seems to stall the entire server (for some reason). This resulted in the addition of `--banner-service-url` parameter in `main` program, so that `bannergen` can run on a separate server to offload computation to completely avoid performance issues caused by `bannergen`, since the worst case would be the compute server stalling and banner requests hanging and failing (which are `await`ed and don't block requests).

Eventually, banner size was reduced to 1700x300 (4x size reduction = 4x more efficient), and several caching mechanisms and optimizations were introduced in the banner generation process, making `bannergen` very lightweight and consume very little resource.

Despite the improvements and demonstrated stability from multiple months of operation, `bannergen` stayed independent and separated as a historical artifact. I have considered migrating back into `main` program, but considering the possibility of reintroducing performance issues, the plan was never executed.
