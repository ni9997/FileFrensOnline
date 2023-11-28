<!-- YOU CAN DELETE EVERYTHING IN THIS PAGE -->
<script lang="ts">
	import FileInfo from '$lib/components/FileInfo/FileInfo.svelte';
	import { FileDropzone, ProgressRadial } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';

	export let data: PageData;

	let filelist: FileList;
	let upload_form: HTMLFormElement;

	// function onChangeHandler(e: Event): void {
	// 	// console.log(e);
	// 	// console.log(filelist);
	// 	// console.log(upload_form);
	// 	// upload_form.requestSubmit();
	// 	// upload_form.requestSubmit
	// 	let data = new FormData();
	// 	// data.append('file', filelist.item(0)?.arrayBuffer())
	// 	fetch('http://localhost:8000/api/upload/', {method: 'POST', body: data});
	// }
	// function test(e: Event): void {
	// 	console.log(e);
	// }
</script>

<div class="flex w-full justify-center items-center xl:max-w-[50%] mx-auto">
	<div class="flex flex-col w-full gap-4 my-4 px-4">
		<form
			class="w-full"
			action="http://localhost:8000/api/upload/"
			method="post"
			enctype="multipart/form-data"
			bind:this={upload_form}
		>
		<div class="flex flex-col gap-2">
			<FileDropzone name="file" />
			<button type="submit" class="btn variant-filled">UPLOAD</button>
		</div>
		</form>
		<!-- <div>TEST</div> -->
		<hr class="!border-t-2" />
		<!-- <div>TEST2</div> -->
		<div class="h-full w-full flex justify-center items-center">
			{#await data.streamed.files}
				<ProgressRadial />
			{:then files}
				<ul class="space-y-4 w-full">
					{#each files as f}
						<FileInfo filename={f}></FileInfo>
					{/each}
				</ul>
			{:catch error}
				{error.message}
			{/await}
			<!-- {data.post.title} -->
		</div>
	</div>
</div>
